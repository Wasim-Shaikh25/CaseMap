# T2 results: `src/layout_structure.py`

**Date:** 2026-09-10
**Code:** `src/layout_structure.py`
**Tests:** `tests/test_layout_structure.py` (4 passed, real-PDF pytest skipped
without Docling in the default interpreter)
**Real pass:** `temp/2026-09-10-structure-t2/run_real.py` on
`venv_docling` + page dump from system PyMuPDF.

## Degrade paths (FR3)

| trigger | tier | how tested |
|---|---|---|
| Docling not importable | `legacy_fallback_internal` | mock `_load_converter` ImportError |
| `convert()` raises | `legacy_fallback_docling_error` | mock converter |
| zero `section_header` items | `legacy_fallback_no_headings` | empty `iterate_items` |
| headings found | `docling_layout` / `confidence=high` | mock 1-indexed `page_no=2` |

All three degrade paths call existing `detect_structure` + `segment_document`.
The success path calls existing `_segment_by_headings`. Docling is **not** added
to `requirements.txt` (HANDOFF §9).

Label matching is substring `"section_header"` (Docling 2.x `SECTION_HEADER`
enum), not exact `== "section_header"`. Page numbers are passed through as-is
(T1: 1-indexed).

## Real fixture PDF

Same 2-page PDF as T1. `segment_document_layered()` returned
`tier: docling_layout`, `heading_count: 4`, one section (all four headings on
page 1, so `_segment_by_headings` groups both pages under the first-page label).
Raw: `temp/2026-09-10-structure-t2/T2_REAL.json`.

## Not done

T3 (Qwen via `sentence_transformers`) and T4 (`poc_run` report wiring).
