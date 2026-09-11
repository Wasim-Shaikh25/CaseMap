# Tasks: fix generic-NER header-block noise in extract_entities()

**Date:** 2026-09-10

## T1 — Exclude the header/cause-title region before running extract_entities()

Implement FR1 (`DESIGN.md`): use `document_profile.extract_cause_title_block()` to
find the header region, exclude it before/while running spaCy NER in
`casemap_pipeline.extract_entities()`. Handle the `None` case (no title block found)
gracefully — falls through to running on the full text, same as today.

**Acceptance:** re-run `extract_entities()` on `testdata/09` and confirm the
malformed multi-line entities (`"THE SUPREME COURT OF INDIA\nCIVIL APPELLATE
JURISDICTION..."`) no longer appear in the output.

## T2 — Add the stoplist (FR2)

Add `GENERIC_ENTITY_TEXT` (exact list in `DESIGN.md`) as a filter, applied to
`PERSON`/`ORG`/`GPE` entities, case-insensitive, before or inside
`normalize_entities()`.

**Acceptance:** none of the 10 stoplist terms appear as a `linked_entities` value in
`detect_events()`'s output on any `testdata/` document.

## T3 — Regression-test the 7 genuine matches (FR3)

**Acceptance:** all 7 genuine cross-document matches listed in `DESIGN.md` still
resolve to the same canonical entity id after T1+T2, verified against real
`testdata/` documents (not synthetic — `FORBIDDEN.md` §E17).

## T4 — Re-run the full 22-document validation

Re-run `temp/2026-09-10-fact-nodes-poc/poc_fact_nodes.py` (or wire the fix into
`src/` first and re-run against a `src/`-based equivalent) against all 22
`testdata/` documents.

**Acceptance:** false cross-document edges materially below the pre-fix baseline of
60 (see `FINDINGS.md` F-8 addendum for the exact baseline numbers to compare
against); the 10 correct bundle edges do not regress.
