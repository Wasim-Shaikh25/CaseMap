# Tasks: Docling-backed structure detection + Qwen3-Embedding similarity

**Date:** 2026-09-09
**Read first:** `REQUIREMENTS.md`, `DESIGN.md`, `POC_RESULTS.md` in this folder.

## T1 — Verify Docling's page-numbering convention against `casemap_pipeline`'s pages

Before writing `layout_structure.py` for real: convert one known multi-page PDF (e.g.
one of `temp/2026-09-09-layer-additions-poc/pdfs/*.pdf`), print each `section_header`
item's `item.prov[0].page_no`, and cross-check it against which
`pages[i]["page_number"]` that heading's text actually appears on (from the same
document processed through `casemap_pipeline`'s existing OCR/page-extraction stage).

**Acceptance:** documented 1:1 correspondence (or a documented off-by-one fix) before
T2 depends on it.

## T2 — `src/layout_structure.py`: `detect_structure_layered()` + `LayeredStructureResult`

Implement per `DESIGN.md`'s sketch — every fallback path reuses existing
`casemap_pipeline` functions (`detect_structure`, `segment_document`,
`_segment_by_headings`), never reimplements them. Three degrade paths required (FR3):
Docling not installed, Docling raises, Docling finds zero headings.

**Acceptance:** unit tests for all three degrade paths (mock/stub Docling for the
"not installed" and "raises" cases) plus one real-document pass through
`segment_document_layered()` end to end.

## T3 — Confirm `Qwen3-Embedding-0.6B` via `sentence_transformers` directly

Try `SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")` standalone, in this project's
real dependency set (not the Ollama path). If it loads and encodes correctly: the fix
is a one-line `make_similarity_fn()` default/parameter change. If not: document why,
and decide (with the owner, since this changes an established seam's behavior) whether
an Ollama-backed second path is worth adding instead.

**Acceptance:** a clear yes/no on the one-line-change question, backed by an actual
run, not inference from the model card.

## T4 — Wire `layout_structure.py` into a real `poc_run.py` pass

Once T1-T3 pass, run `scripts/poc_run.py` against a real multi-document set (start
with the 3-document connected bundle, `testdata/09`/`21`/`22`, rendered to PDF via
`temp/2026-09-09-layer-additions-poc/make_test_pdfs.py` or equivalent) with the new
`layout_structure.py` present, and confirm `segment_document_layered()`'s `meta`
(`tier`/`confidence`) is visible in whatever `poc_run.py` writes to
`poc_report.md`/`poc_graph.json` — satisfying NFR2, not just present in a Python dict
that nothing downstream reads.

**Acceptance:** a real `poc_report.md`/`poc_graph.json` run showing `tier: "docling_layout"`
for at least one document, and the legacy tier for at least one control case (e.g. a
document with Docling artificially disabled) — proving both paths are actually
reachable, not just one.

## Explicitly deferred (not in this task list)

- MinerU comparison — separate requirement if pursued.
- Coordinating Docling's own OCR with `casemap_pipeline`'s existing OCR ladder — this
  task list only uses Docling for structure detection on already-extracted page text.
- React Flow / evidence-card rendering of structure-detection confidence — stage [6]
  isn't built yet.
