# POC results: Docling + Qwen3-Embedding

**Date:** 2026-09-09
**Full write-up:** `docs/research/new-directions/layer-additions-assessment.md` (all 4
parts) — this file is a pointer + acceptance-relevant summary, not a duplicate.
**Logged finding:** `FINDINGS.md` F-4.

## What was actually validated

- Docling (2.126.0) correctly labelled headings (`section_header`) and numbered
  paragraphs (`list_item`) on 4 digitally-rendered PDFs with a real font hierarchy
  (Part 1), **and** on 2 genuinely rasterized-and-degraded PDFs with zero embedded
  text layer, forcing real OCR (Part 4) — real rotation, blur, and salt-and-pepper
  noise, verified 0 characters in the text layer before the run.
- `qwen3-embedding:0.6b` (via Ollama) dropped into `casemap_pipeline.score_pair()`'s
  `similarity_fn` seam and, combined with Docling's structure + `en_legal_ner_sm`'s
  entities, correctly linked 3 genuinely connected real documents while correctly
  leaving an unrelated document unconnected — through the real, unmodified
  `casemap_pipeline` graph functions (Part 3).

## What was NOT validated — read before starting `TASKS.md`

1. **`item.prov[0].page_no` page-numbering convention was never cross-checked**
   against `casemap_pipeline`'s own `pages[i]["page_number"]` — the POC scripts only
   counted/printed items, never grouped them back onto real page objects. `DESIGN.md`
   flags this as the first thing to verify.
2. **Qwen3-Embedding was only tested via Ollama's HTTP API**, not via
   `sentence_transformers.SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")` — the
   actual code path `make_similarity_fn()` uses. Whether this is a one-line
   `model_name` change or needs new code is genuinely unknown until tried.
3. **Only 4-6 total documents tested across all 4 parts.** Real implementation should
   re-run against a larger slice of `testdata/` (22 documents) once wired through the
   real `layout_structure.py` module, not just standalone POC scripts.
4. Docling's OCR (RapidOCR) was exercised in Part 4, but **only in isolation** —
   never coordinated with `casemap_pipeline`'s own existing OCR ladder
   (PaddleOCR/Surya/Tesseract), which is what actually produces the `pages` text this
   design's `detect_structure_layered()` receives as input. This design uses Docling
   for structure only, given already-extracted page text — see `DESIGN.md`'s
   "explicitly deferred" section.
