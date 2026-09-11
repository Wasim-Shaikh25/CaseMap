# Design: project `.venv`, reuse the existing installer

**Date:** 2026-09-10

Do not add a second NER load path. `opennyai_bridge.load_opennyai_ner()` stays
eager-raise-by-default.

1. `py -3.11 -m venv .venv` at repo root (ephemeral to this machine; not a
   committed artifact — note in `.gitignore` if one exists, else document).
2. `.venv` pip: `-r requirements.txt`, then `scripts/install_en_legal_ner_sm.py`,
   then `python -m spacy download en_core_web_sm` (generic NER, already used by
   `extract_entities()`).
3. README "Picking this up" names `.venv` as the default, `venv_ner` as the
   historical POC env.

`--allow-degraded` remains for interpreters that have not run the installer.
