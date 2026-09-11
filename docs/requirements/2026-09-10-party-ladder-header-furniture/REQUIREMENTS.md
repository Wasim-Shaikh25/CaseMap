# Requirements: `extract_parties_layered()` caption-furniture as parties

**Date:** 2026-09-10
**For:** a confirmed bug in existing `src/` code (`CHANGELOG.md` entry 26,
`HANDOFF.md` §1). Not an upgrade.
**Read first:** `FORBIDDEN.md` §E15, `FINDINGS.md` F-8 (same family, different
function), `docs/requirements/2026-09-10-residual-false-edges/`.

## The bug, precisely

`document_profile.extract_parties_layered()` (the regex-only 5-tier ladder) treats
indiankanoon **caption furniture** as parties. Documented on real `testdata/`:

- `"Author: Y.V. Chandrachud"` as Petitioner (`testdata/01_…`)
- `"CITATION"` as Respondent (the `CITATION:` heading below the cause title)

This is **confidently wrong** (`FORBIDDEN.md` §E15) — a judge byline and a
section label, not litigants. The mandatory hybrid path can emit the same
`Author:` span when ML NER labels it PETITIONER (`temp/2026-09-10-ui-poc/poc_report.md`
on doc 09). The ladder is the named defect; the furniture filter must also
apply to hybrid output so the UI dossier path is not left wrong.

This is **not** the F-8 `extract_entities()` bug (generic spaCy NER on headers).
It is the same *family*: caption/metadata lines fed into an extractor meant for
party names. The F-8 “skip the whole title-block” shape is **wrong here** —
the cause title *is* where real party names live. Skipping
`extract_cause_title_block` would drop genuine parties.

## Goal

Furniture lines and indiankanoon section labels must never appear in
`PartyResult.parties`. Real cause-title names on `testdata/` (e.g. Dilip Kumar
Sharma / State of Madhya Pradesh on doc 01; Vijay Kumar Singhania / Bank of
Baroda on doc 09) must still extract.

## Non-goals

- Not skipping the cause-title region (that is the F-8 NER skip; inverted here).
- Not making OpenNyAI optional (`FORBIDDEN.md` §E16).
- Not UI / FastAPI.
- Not a stoplist of judge surnames.

## Functional requirements

1. **FR1** — Caption furniture lines in the first ~40 lines
   (`Author:`, `Equivalent citations`, `Bench:`, `Source:`, `REPORTABLE`) are
   not grouped as party entries. Versus-block walks stop *before* those lines
   (same furniture class as `casemap_pipeline._FURNITURE_LINE_RE`, tightened
   so `Author:` does not match “Authorised Officer”).
2. **FR2** — Indiankanoon section headings (`CITATION:`, `CITATOR INFO`,
   `DATE OF JUDGMENT`, standalone `ACT`) end the below-versus walk. They are
   not party names.
3. **FR3** — If a tier’s only “parties” were furniture, do not return them at
   high/medium confidence — fall through the ladder (`FORBIDDEN.md` §E15).
4. **FR4** — `extract_parties_hybrid()` drops the same furniture names from
   ML output (doc 09 `Author: Ashok Bhushan` as Petitioner).

## Acceptance / validation

Against real `testdata/` (not synthetic-only, `FORBIDDEN.md` §E17):

- Doc 01: no party named `Author:…` / `CITATION`; Dilip Kumar Sharma and
  State of Madhya Pradesh still present on the layered path.
- Doc 09: no `Author: Ashok Bhushan` on layered (and hybrid, if the model
  loads).
- Full 22-doc scan: zero party names matching furniture/section patterns.
