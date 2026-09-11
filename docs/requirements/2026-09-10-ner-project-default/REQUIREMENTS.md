# Requirements: project-default NER environment

**Date:** 2026-09-10
**Follows:** `docs/requirements/2026-09-10-wire-opennyai-ner/` (installer +
`venv_ner` proof). **New folder** — do not retrofit that one (`AGENTS.md` §6).
**Read first:** `FORBIDDEN.md` §E16, `HEART.md` tier 1, `HANDOFF.md` §6.

## Problem

`load_opennyai_ner()` already raises by default if the model is missing. The
installer and a working load exist only in
`temp/2026-09-09-mini-llm-poc/venv_ner/`. System Python is known-broken
(spaCy/pydantic). There is no project-root venv, so a cold `python scripts/poc_run.py`
on this machine is still `--allow-degraded` unless the agent remembers the temp path.

## Goal

A **project-root `.venv`** that is the documented default interpreter: after
`requirements.txt` + `scripts/install_en_legal_ner_sm.py`, default
`load_opennyai_ner()` succeeds **without** `--allow-degraded`. Do not install
into system Python (same non-goal as the previous folder). Do not put the
invalid HuggingFace wheel in `requirements.txt`.

## Non-goals

- Not making NER optional.
- Not claiming `real_pdfs/` OCR proof (`HANDOFF.md` §6 still absent).
- Not pinning Docling.

## Functional requirements

1. **FR1** — `.venv` at repo root, created with this machine's Python 3.11.
2. **FR2** — That venv can `spacy.load("en_legal_ner_sm")` and
   `load_opennyai_ner()` with `allow_degraded=False`.
3. **FR3** — README (or equivalent picking-this-up note) says: use `.venv`,
   run the installer after `pip install -r requirements.txt`, do not use
   `--allow-degraded` for a real pipeline run.

## Acceptance

From `.venv`:
`python -c "import sys; sys.path.insert(0,'src'); from opennyai_bridge import load_opennyai_ner; print(load_opennyai_ner().meta['name'])"`
prints the model name and does not raise.
