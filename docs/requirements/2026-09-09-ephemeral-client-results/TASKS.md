# Tasks: ephemeral client results

**Date:** 2026-09-09
Read `REQUIREMENTS.md` and `DESIGN.md` first. Do not start FastAPI/UI tasks until
`HEART.md` tier 1 is proven, or the owner dates a skip-tier decision.

## T1 — Record the constraint in live specs (this session)

Add a dated amendment on `docs/spec/SCOPE.md` and a guardrail on
`docs/spec/ARCHITECTURE.md` so the no-server-retention rule is citable, not only
in this folder.

**Acceptance:** SCOPE amendment log and ARCHITECTURE G4 both name: multi-doc
upload → return processed payload → client persistence → delete PDFs; cookies
are not the graph store.

## T2 — (blocked) Per-request temp + OCR-cache scoping

When a processing service is built: request-scoped temp directory; delete on
success and failure; confirm `.casemap_ocr_cache` cannot leak another user's
pages. Not started — blocked on HEART tier 3.

## T3 — (blocked) Client persistence (IndexedDB or file download)

Store returned JSON on the client; user can reopen without the server. Not
cookies. Not started.

## T4 — (blocked) Multi-file upload wired to the real pipeline

Bundle upload calling existing `src/` functions, response body = graph JSON.
Not started.
