# Requirements — HANDOFF §9 petition follow-ups (F-12)

**Date:** 2026-09-10
**For:** owner-approved next steps in `HANDOFF.md` §9 after F-12.
**Read first:** `FINDINGS.md` F-12, `FORBIDDEN.md` §E17, `HANDOFF.md` §0/§9/§10.

## Problem

F-12 fixed numbered headings and single-page `.txt` segmentation on **one**
real filed petition (personal; stays under `temp/`, never `testdata/`). Four
follow-ups were left open:

1. MiniLM vs Qwen important-line agreement was 60% on that one document.
2. Party extraction and `case_symbols.normalize_name()` were not checked on a
   petition-shaped cause title / affidavit deponent.
3. Heading conventions other than roman/numeric prefixes (`A. GROUNDS`,
   `(vii) GROUNDS`, official SC form wording) were not measured.
4. Multi-page **PDF** ingestion of a petition (per-page headings) was not
   exercised — only one-page `.txt`.

## Goal

Measure all four against real sources. Change `src/` only when a miss is
shown on a real court-published form or the real petition, with a reason that
predates the patch. Do not invent a second petition. Do not copy the personal
petition into `testdata/`. Do not build UI.

## Non-goals

- Not switching `EMBED_MODEL_NAME` without a new dated owner decision.
- Not adopting Docling as a `requirements.txt` pin (`HANDOFF.md` §10).
- Not widening `ANNEXURE_PATTERN` for lettered/parenthetical prefixes unless
  a real document uses them.
