# Tracker: fallback nodes stay on the graph, honestly labeled

Ticked live as work happens — per `AGENTS.md` §6, this is not written in advance and
back-filled; update it in the same change that does the work.

| Task | Status | Date | Notes |
|---|---|---|---|
| REQUIREMENTS.md | Done | 2026-09-09 | |
| DESIGN.md | Done | 2026-09-09 | Grounded in real `src/` code, not assumptions |
| POC (mechanism) | Done | 2026-09-09 | `FINDINGS.md` F-3 |
| POC (edge formation) | Done | 2026-09-09 | Conditional on `normalize_entities()` — see T3 |
| T1 — `party_result_to_fallback_event()` | Done | 2026-09-09 | `src/document_profile.py`; `tests/test_fallback_event.py` (3 passed). Also calls `normalize_entities()` (T3 implementation landed here; T3 real-bundle acceptance still open). |
| T2 — ML role-instability trigger | Done | 2026-09-10 | `extract_parties_hybrid` stamps `ml_role_unstable`; testdata 01/12/16/17 all produce fallback events |
| T3 — `normalize_entities()` call | Done | 2026-09-10 | Canonical keys + party PERSON names; doc 22 links to 09/21, control does not |
| T4 — confidence rendering | Done | 2026-09-10 | `to_react_flow` / `build_evidence_card` expose `confidence` (`resolved` vs fallback stamp) |
| T5 — wire into `poc_run.py` | Done | 2026-09-10 | `.txt` inputs + `party_result_to_fallback_event` appended to events |

**Current state (2026-09-10):** T1–T5 done.
