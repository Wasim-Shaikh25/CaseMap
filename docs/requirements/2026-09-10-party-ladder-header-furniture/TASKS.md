# Tasks

## T1 — Furniture + section-label guards in the ladder

Implement DESIGN.md in `src/document_profile.py`.

**Acceptance:** `extract_parties_layered` on `testdata/01` and `testdata/09`
emits no `Author:` / `CITATION` parties; real litigant names remain.

## T2 — Hybrid ML post-filter (FR4)

Same filter on `extract_parties_hybrid` ML output.

**Acceptance:** if `en_legal_ner_sm` loads, doc 09 has no `Author: Ashok Bhushan`
in `parties`. Skip the ML assertion if the model is missing (layered T1 still
binds).

## T3 — 22-doc sweep

Run `extract_parties_layered` on all `testdata/*.txt`.

**Acceptance:** no party name matches caption furniture or `CITATION`/`CITATOR INFO`.
