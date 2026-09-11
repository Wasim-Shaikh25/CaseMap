# Requirements: residual false edges after header-block skip

**Date:** 2026-09-10
**Follows:** `docs/requirements/2026-09-10-entity-extraction-header-noise/` T4
(false edges 60→24). This folder is a **new** unit of work — not a retrofit of
that one (`AGENTS.md` §6).
**Read first:** `FORBIDDEN.md`, `FINDINGS.md` F-8.

## The bug, diagnosed on the real leftover 24 edges

After T1–T4 of the previous requirement, a 22-doc re-run still had 24 false
cross-document edges. Every one of them is entity-score 1.0 from **three strings
only** (not 24 independent bugs):

1. `"THE SUPREME COURT OF INDIA"` — forum caption left **before**
   `extract_cause_title_block`'s `line_start` (the previous fix excluded
   `line_start`–`line_end` only, so REPORTABLE / `IN THE SUPREME COURT OF INDIA`
   / indiankanoon `Equivalent citations` / `Bench:` still went through generic NER).
2. `"AIR 20xx SUPREME COURT"` — reporter citations on the `Equivalent citations:`
   line, labelled ORG.
3. `"R. Subhash"` — truncated bench-judge fragment from `Bench: … R. Subhash Reddy`
   shared by two unrelated Supreme Court benches.

## Goal

Drive those 24 false edges to **zero** (or as close as the same 22-doc protocol
allows) without regressing the 09/21/22 bundle's correct edges or FR3 body names
(`Bank of Baroda`, `National Company Law Tribunal`).

## Non-goals

- Not a longer one-off stoplist of judge names.
- Not changing `score_pair` weights to hide the problem.
- Not FastAPI/UI.

## Functional requirements

1. **FR1** — Generic NER must not run on the **preamble through the cause title**
   (character offset 0 through `TitleBlock.line_end`), not only the versus-bounded
   interior. If no title block, still skip indiankanoon furniture lines
   (`Equivalent citations`, `Author`, `Bench`, `REPORTABLE`) in the first 40 lines.
2. **FR2** — Drop reporter-shaped spans (`AIR` + year) even if they appear outside
   that region. A citation is not a party.
3. **FR3** — Same genuine-match regression as the previous requirement: body names
   in the 09/21/22 bundle must still extract and share ids.
