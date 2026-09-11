# Design: ephemeral processing (constraint for future tier 3)

**Date:** 2026-09-09
**Requirements:** `REQUIREMENTS.md` in this folder.

## Why this is design-now, build-later

`HEART.md` tier 3 (FastAPI + React Flow + PDF.js) is not started. `AGENTS.md` §4
forbids building that UI ahead of a proven tier 1. This DESIGN.md exists so the
owner's 2026-09-09 instruction is not lost in chat, and so a later agent cannot
treat SQLite/`casemap.db` or a `uploads/` folder as a product database.

## Processing flow (when the service exists)

```
client: select N documents
   │
   ▼
POST multipart (or equivalent) — files live in a request-scoped temp dir
   │
   ▼
existing pipeline (casemap_pipeline / document_profile / opennyai_bridge)
   │
   ▼
response: graph JSON + evidence cards (same shape as poc_graph.json)
   │
   ├── client: persist payload in IndexedDB (or File System Access / download)
   └── server: delete temp dir (PDFs + any OCR cache written for this request)
```

`scripts/poc_run.py` already writes `poc_graph.json`. The service, when built, should
call that pipeline (or the same functions) and return that object, not invent a
second output schema.

## Client storage (not cookies)

A case-map payload will exceed cookie limits. Use **IndexedDB** (or a user-chosen
download of the JSON file) as the place of record. Cookies are out for the graph.

## Server SQLite

`casemap.db` today is the bi-temporal edge store for a pipeline run. Under this
constraint it must be **per-request / ephemeral** (temp file deleted with the
request), not a long-lived catalog of user cases. That is a later implementation
detail; do not silently start writing user graphs into a repo-root `casemap.db`.

## Unverified assumption (do not skip)

- Whether the current OCR cache (`.casemap_ocr_cache` in `casemap_pipeline.py`)
  would retain page images/text across requests if a FastAPI process is long-lived.
  **T1 of implementation (when allowed) must verify and disable or scope that cache
  per request**, or it would violate FR4 without anyone noticing.
