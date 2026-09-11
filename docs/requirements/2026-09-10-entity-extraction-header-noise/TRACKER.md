# Tracker: fix generic-NER header-block noise in extract_entities()

Ticked live as work happens — per `AGENTS.md` §6.

| Task | Status | Date | Notes |
|---|---|---|---|
| REQUIREMENTS.md | Done | 2026-09-10 | |
| DESIGN.md | Done | 2026-09-10 | |
| T1 — exclude header region | Done | 2026-09-10 | `extract_entities` skips `extract_cause_title_block` char range; also drops newline-containing NER spans |
| T2 — stoplist | Done | 2026-09-10 | `GENERIC_ENTITY_TEXT` in `extract_entities` and `normalize_entities` |
| T3 — regression test 7 genuine matches | Done | 2026-09-10 | `tests/test_extract_entities_header_noise.py`; body-expected names still present; no id splits |
| T4 — full 22-doc re-validation | Done | 2026-09-10 | false cross-doc 60→24; correct bundle 10→14 |

**Current state (2026-09-10):** T1–T4 implemented and validated against all 22
`testdata/` documents. Residual 24 false cross-document edges remain (F-8 not fully
closed).
