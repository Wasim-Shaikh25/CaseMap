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
| T3 — Qwen3-Embedding via `sentence_transformers` | Evaluated, decision pending | 2026-09-10 | ST path run for real against `testdata/` excerpts (`FINDINGS.md` F-10 update): Qwen separates same-matter from unrelated pairs by roughly double the current default's margin (~0.41 vs ~0.24 spread). `EMBED_MODEL` in `src/casemap_service.py` is still `all-MiniLM-L6-v2` — adopting Qwen as the pipeline default needs the owner's explicit sign-off (`HANDOFF.md` §10), not more evaluation. |
| T4 — wire into `poc_run.py` | Done | 2026-09-10 | Markdown table already had tier; `poc_graph.json` now has `documents[].structure_tier` |

**Current state (2026-09-11):** T1, T2, T4 done. T3 (Qwen via `sentence_transformers`)
evaluated with a real result in favor of the upgrade, but not adopted — an explicit
owner decision, not more engineering, is what's left. Docling is still not installed
in the project's own `.venv` (confirmed 2026-09-11: `import docling` fails there) —
still not a permanent `requirements.txt` pin (HANDOFF §9); T2 degrades to a
non-Docling tier if it is missing.
