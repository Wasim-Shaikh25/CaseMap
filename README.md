# CaseMap

A source-grounded, LLM-free-in-the-core visual case-file map for legal document
bundles — every extracted fact traces to a verbatim source span with page/char
provenance, and nothing is invented.

Upload a bundle of PDFs, Word documents, or `.txt` filings and CaseMap turns it
into a verbatim, page-and-paragraph-cited timeline, document breakdown,
cross-document provision/citation list, party ladder, and conflict view —
every fact is a direct excerpt from the source with an exact reference back to
it. It runs entirely on your machine: nothing you upload is kept on the
backend after it answers, and the only thing that ever leaves your device is
an anonymous page-load counter (no document data, ever).

## The laws (read these first)

See `THESIS.md` and `HEART.md` for the full statement. In short:

1. No LLM (generative model) may ever generate, paraphrase, or infer party names,
   dates, amounts, provisions, events, or graph edges in the extraction/graph core —
   only select verbatim spans that validate against source text with char offsets.
2. OpenNyAI's Legal NER is a mandatory extraction/labelling layer, not an optional
   fallback tier.
3. Real documents (`real_docs/`, `real_pdfs/`) are the only valid test oracle. A
   confidently-wrong result is a worse failure than an honest "don't know."

## Quick start (Windows, one command)

```powershell
.\run.ps1
```

This one script installs everything and starts the app:

1. Creates `.venv` (Python 3.11) if it doesn't exist yet.
2. Installs the core pipeline dependencies (`requirements.txt`) and the web
   app dependencies (`requirements-webapp.txt`).
3. Installs the **mandatory** OpenNyAI legal-NER model (`en_legal_ner_sm`) if
   it isn't already present.
4. Downloads spaCy's `en_core_web_sm` if it isn't already present.
5. Checks whether the system Tesseract OCR binary is on `PATH` (only needed
   for genuinely **scanned** PDFs — digital PDFs, `.docx`, and `.txt` all
   work without it) and warns, without failing, if it's missing.
6. Starts the app at **http://127.0.0.1:8756** and opens it in your browser.

There is only **one process** to run: `server/app.py` mounts `ui/` as static
files, so the same FastAPI server *is* the frontend — there's no separate
frontend dev server, no `npm install`, nothing else to start.

Useful flags:

```powershell
.\run.ps1 -Port 9000        # run on a different port
.\run.ps1 -NoBrowser         # don't auto-open the browser
.\run.ps1 -IncludeDocling    # also install the optional, heavy (~1.5GB)
                             # Docling structure layer — see
                             # requirements-docling.txt's own header first;
                             # it has not been verified installed alongside
                             # the mandatory NER chain above.
```

First run downloads several ML models (spaCy, sentence-transformers, GLiNER,
the SaT boundary model) and can take a few minutes and a few GB of disk.
Every run after that is fast — the script only installs what's missing.

### If you'd rather do it by hand (or you're not on Windows)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r requirements-webapp.txt
.venv\Scripts\python.exe scripts\install_en_legal_ner_sm.py
.venv\Scripts\python.exe -m spacy download en_core_web_sm
.venv\Scripts\python.exe -m uvicorn server.app:app --port 8756
```

Then open http://127.0.0.1:8756. On macOS/Linux, use `.venv/bin/python` in
place of `.venv\Scripts\python.exe` and install Tesseract via your package
manager (`brew install tesseract` / `apt install tesseract-ocr`) if you'll
process scanned PDFs.

`en_legal_ner_sm` cannot go in `requirements.txt` — HuggingFace serves it as a
wheel with an invalid PEP 440 version segment that pip rejects outright, so it
needs its own install step (`scripts/install_en_legal_ner_sm.py` handles the
whole recipe, including re-pinning spaCy afterward). Real pipeline runs must
**not** pass `--allow-degraded` if you want the real model, not the
regex-only fallback.

## Using the app

1. Click **+ New case**, pick or drag in a bundle of PDFs/`.docx`/`.txt`
   files, and wait for processing (a progress state shows while the
   pipeline runs).
2. The case view gives you: a **timeline** of dated events, a
   **documents** breakdown per file (structure tier, parties, sections),
   **provisions cited** across the whole bundle, a **parties** ladder, and
   a **conflicts** view (asserts vs. denies on the same fact).
   - Optional, off by default: on the upload screen, **"Look up cited
     provisions online"** fetches each cited provision's own text from
     IndianKanoon.org (one call per unique citation — only the citation
     string leaves the device, e.g. "Section 125 CrPC", never document
     content), shown inline in **Provisions cited**. Skipped automatically
     whenever a match isn't clear rather than guessing (`src/provision_lookup.py`).
3. Click any node to open the **evidence drawer** — the verbatim source
   text with page/paragraph and a highlighted exact excerpt, never a
   paraphrase.
4. If the case was opened via the file picker (not drag-and-drop) in
   Chrome/Edge, a **↻ Reprocess** button re-runs extraction from the same
   files on disk without re-browsing.
5. Everything is saved only in your browser's `localStorage` — closing the
   tab doesn't lose your cases, but nothing is synced anywhere.

## Running the tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Documents

- `THESIS.md` — the laws · `HEART.md` — what we want + build tiers
- `docs/spec/SCOPE.md` — the boundary · `docs/spec/ARCHITECTURE.md` — the build spec
- `FORBIDDEN.md` — the mistakes we never repeat · `AGENTS.md` — binding rules
- `STATUS.md` — current state · `CHANGELOG.md` — history · `FINDINGS.md` — the register
- `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` — the deep pre-governance technical handoff (architecture,
  full 26-bug ledger, real-document dry-run results, open gaps) — still authoritative
  for implementation detail
- `docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md` — the mandatory OpenNyAI NER layer, in depth
- `docs/research/existing-approach/poc_report.md` — the most recent POC run's output

## Architecture, in one paragraph

`src/casemap_service.py` is the single shared pipeline: `process_document()`
(structure segmentation → deterministic extraction → the mandatory OpenNyAI
NER layer → SaT sentence-boundary refinement → rhetorical-role tagging) and
`build_case_graph()` (cross-document candidate scoring → the cross-document
entity gate → the React-Flow-shaped graph). `server/app.py` is a thin FastAPI
wrapper over it that also serves `ui/` as static files (so it's the whole
app, frontend included). `scripts/poc_run.py` is a thin CLI wrapper over the
same pipeline, used for proof/report runs and the bi-temporal
(`TemporalEdge`/SQLite) experiment, which is deliberately CLI-only and never
wired into the server (it would violate the server's "nothing is persisted"
contract — see `FINDINGS.md` F-5/F-14).

## Picking this up

`HANDOFF.md` is the orientation document: where the project stands, open findings, the
work queue, known traps, and what's reserved for the project owner. Read `FORBIDDEN.md`
and `AGENTS.md` first — those are binding; the handoff is the map.
