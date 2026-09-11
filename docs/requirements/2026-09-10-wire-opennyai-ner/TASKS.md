# Tasks

## T1 — Fix `NER_INSTALL_CMD` / `_fail()` message

Point at `scripts/install_en_legal_ner_sm.py` and the rename recipe, not the
invalid HuggingFace URL as a one-liner `pip install`.

## T2 — `scripts/install_en_legal_ner_sm.py`

Implements DESIGN.md. Downloads into `temp/` (ephemeral), not `src/`.

## T3 — Verify `load_opennyai_ner()` default path on `venv_ner`

**Acceptance:** default load (no `allow_degraded`) succeeds; model name printed.
