# Requirements: wire `en_legal_ner_sm` into the real pipeline load path

**Date:** 2026-09-10
**Read first:** `FORBIDDEN.md` §E16, `HANDOFF.md` §8 item 2, `FINDINGS.md` F-2,
`docs/research/new-directions/mini-llm-extraction-assessment.md` Part 2.

## Problem

`opennyai_bridge.load_opennyai_ner()` already raises by default if the model is
missing (`--allow-degraded` is the only escape hatch). F-2 proved the model loads
and runs on real documents — **only** in `temp/2026-09-09-mini-llm-poc/venv_ner/`.
The HuggingFace wheel cannot live in `requirements.txt` (invalid PEP 440
`any` version). `NER_INSTALL_CMD` still tells people to `pip install` that URL,
which current pip rejects.

## Goal

A documented, runnable install path so `load_opennyai_ner()` succeeds without
`--allow-degraded` in an environment that followed the recipe — without making the
NER optional (`FORBIDDEN.md` §E16).

## Non-goals

- Not making OpenNyAI optional.
- Not claiming accuracy is proven on `real_pdfs/` (still absent).
- Not installing into every Python on this machine (system spaCy/pydantic conflict).

## Functional requirements

1. **FR1** — `NER_INSTALL_CMD` / `_fail()` must describe an install that actually
   works (rename the wheel, then re-pin spaCy 3.8.x), not the URL pip rejects.
2. **FR2** — A `scripts/` installer implements that recipe.
3. **FR3** — `load_opennyai_ner()` with default `allow_degraded=False` succeeds in
   the known-good env (`venv_ner`) and returns a real spaCy pipeline.

## Acceptance

`python -c "from opennyai_bridge import load_opennyai_ner; n=load_opennyai_ner(); print(n.meta['name'])"`
from `src/` on the working venv prints the model name and does not raise.
