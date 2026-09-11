# Tracker: Docling-backed structure detection + Qwen3-Embedding similarity

Ticked live as work happens — per `AGENTS.md` §6.

| Task | Status | Date | Notes |
|---|---|---|---|
| REQUIREMENTS.md | Done | 2026-09-09 | |
| DESIGN.md | Done | 2026-09-09 | Grounded in the real `segment_document_layered()` seam |
| POC (Docling, clean PDFs) | Done | 2026-09-09 | `FINDINGS.md` F-4, Part 1 |
| POC (Qwen3-Embedding, Ollama path) | Done | 2026-09-09 | `FINDINGS.md` F-4, Part 2-3 |
| POC (Docling, genuinely scanned PDFs) | Done | 2026-09-09 | `FINDINGS.md` F-4, Part 4 |
| T1 — page-numbering verification | Done | 2026-09-10 | 1-indexed; 4/4 agree on 2-page fixture. See T1_RESULTS.md |
| T2 — `layout_structure.py` implementation | Done | 2026-09-10 | `src/layout_structure.py`; T2_RESULTS.md; Docling still optional |
| T3 — Qwen3-Embedding via `sentence_transformers` | Not started | | Ollama path tested; ST path not yet tried |
| T4 — wire into `poc_run.py` | Done | 2026-09-10 | Markdown table already had tier; `poc_graph.json` now has `documents[].structure_tier` |

**Current state (2026-09-10):** T1–T2 and T4 done. T3 (Qwen via `sentence_transformers`) not started — owner deprioritized (evaluation only; does not ship). Docling is still
not a permanent `requirements.txt` pin (HANDOFF §9); T2 degrades if it is missing.
