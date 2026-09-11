"""server/app.py — CaseMap local processing backend (HTTP wrapper).

A thin FastAPI layer over `src/casemap_service.py`, which holds the ONE
processing pipeline (shared with `scripts/poc_run.py`). This file adds no
pipeline logic — only HTTP concerns: upload handling, the per-request temp
dir, CORS, the no-cache middleware, health, and serving the `ui/` folder.

Privacy contract (see FINDINGS.md F-5 — no server retention of uploads):
  - Uploaded files are written to a per-request temp directory and deleted
    in a `finally` block, success or failure.
  - Nothing is written to casemap.db / poc_graph.json / disk. The only
    output is the JSON response body. (casemap_service persists nothing;
    the bi-temporal SQLite write lives only in the poc_run.py CLI wrapper.)
  - The server keeps no in-memory history across requests — no session
    store, no cache of document text. Persistence is the browser's job
    (localStorage in ui/app.js), not this server's.
  - This holds whether the server is bound to 127.0.0.1 for local use today
    or later deployed for real users over the internet — the contract is
    "never persist the document", not "only promise that on localhost".

Run: uvicorn server.app:app --reload --port 8756   (from the project root)
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import traceback

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import casemap_service as service

ALLOWED_EXT = {".pdf", ".docx", ".doc", ".txt"}

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _read_version() -> str:
    try:
        with open(os.path.join(_ROOT, "VERSION")) as f:
            return f.read().strip()
    except OSError:
        return "unknown"


APP_VERSION = _read_version()
# Render sets RENDER_GIT_COMMIT automatically; a bare VPS checkout has none,
# so this is best-effort provenance, not a hard requirement.
GIT_COMMIT = os.environ.get("RENDER_GIT_COMMIT", "")[:12] or "unknown"

# Load every ML layer (NER, SaT boundary judge, GLiNER party judge, MiniLM
# embedder) once at process startup instead of on whichever request happens
# to touch each one first. On always-on hardware with RAM to spare (a VPS)
# this means the first real request isn't the one that pays every model's
# load latency AND memory spike at once -- the exact combination that
# OOM-crashed the Render free-tier instance mid-request (2026-09-11).
# Default on; set WARM_MODELS_ON_START=false to keep the old lazy behavior
# (e.g. a memory-constrained host where failing fast at boot isn't wanted).
WARM_MODELS_ON_START = os.environ.get("WARM_MODELS_ON_START", "true").strip().lower() not in (
    "0", "false", "no")

app = FastAPI(title="CaseMap backend")


@app.on_event("startup")
async def _warm_models_on_start():
    if WARM_MODELS_ON_START:
        service.warm_all_models()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8756", "http://localhost:8756"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def _no_cache_ui_assets(request, call_next):
    # This app is under active iteration — a browser caching index.html/
    # app.js/styles.css aggressively makes a real refresh look like it did
    # nothing, which reads as "I can't even refresh." Force revalidation on
    # every request for the UI files (cheap: they're tiny local files).
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.get("/api/health")
def health():
    status = service.layer_status()
    status["version"] = APP_VERSION
    status["commit"] = GIT_COMMIT
    return status


@app.post("/api/process")
async def process(files: list[UploadFile] = File(...),
                  lookup_provisions: bool = Form(False)):
    """`lookup_provisions`: opt-in only (see provision_lookup.py /
    ui/index.html's disclosure text) — when true, each cited provision's own
    text is fetched from IndianKanoon.org, one call per unique citation.
    Only the citation string leaves the device; no document content."""
    t0 = time.time()
    bad = [f.filename for f in files
           if os.path.splitext(f.filename or "")[1].lower() not in ALLOWED_EXT]
    if bad:
        return JSONResponse(
            {"error": f"Unsupported file type: {', '.join(bad)}. "
                      f"Only PDF, Word (.docx), and .txt are accepted."},
            status_code=400)

    ml_nlp = service.get_ml_nlp()
    tmpdir = tempfile.mkdtemp(prefix="casemap_upload_")
    try:
        doc_results = []
        all_events: list[dict] = []

        for f in files:
            name = f.filename
            dest = os.path.join(tmpdir, name)
            with open(dest, "wb") as out:
                out.write(await f.read())

            try:
                doc = service.process_document(dest, name, ml_nlp, ocr_engine="tesseract",
                                               lookup_provisions=lookup_provisions)
            except Exception as exc:
                traceback.print_exc()
                doc_results.append({"name": name, "error": str(exc)})
                continue

            all_events.extend(doc.pop("events"))
            doc_results.append(doc)

        graph = service.build_case_graph(doc_results, all_events)
        graph["runtime_s"] = round(time.time() - t0, 1)
        graph["ml_layer"] = "active" if ml_nlp is not None else "degraded"
        return graph
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# Serve the separated ui/ folder at "/" — same-origin, so the browser page
# can call /api/* with no CORS gymnastics. Mounted last so /api/* wins.
_UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ui")
app.mount("/", StaticFiles(directory=_UI_DIR, html=True), name="ui")
