# Design: skip caption furniture; do not skip the cause title

**Date:** 2026-09-10
**Requirements:** `REQUIREMENTS.md` in this folder.

## Why not “exclude `extract_cause_title_block`”

F-8 / residual-false-edges excluded `[0, title-block-end)` so **generic NER**
would not see headers. Party extraction **must** see the versus-bounded cause
title. Reusing that skip would delete the signal.

The residual-false-edges piece that *does* transfer is furniture-line handling:
`Author:` / `Bench:` sit **above** the versus block; `CITATION:` sits **below**
it. `_block_bounds_above` currently walks into `Author:` (TITLE_TOP does not
match `Author: Y.V. Chandrachud`). `_block_bounds_below` / `BODY_START_RE`
do not treat `CITATION:` as body start, so `_group_entries` emits it as a name.

## Change (in `document_profile.py`)

1. `_is_caption_furniture_line` / `_is_caption_section_label` — shared
   predicates (do not import `casemap_pipeline`; that module already imports
   this one).
2. `_block_bounds_above`: treat furniture as a hard top (like TITLE_TOP),
   without including the furniture line.
3. `_block_bounds_below`: treat section labels as body start.
4. `_group_entries` and `_looks_like_party_name`: skip those lines/names.
5. `_filter_caption_furniture_parties`: post-filter on every non-empty
   `extract_parties_layered` tier return and on hybrid ML `refined` lists.
   Empty after filter → fall through (FR3).

No new dependencies. No generative model. Spans remain verbatim names that
survived the filter.

## Regression

Cause-title names that are not furniture must still appear. Doc 01/09 are the
oracle rows. A 22-doc sweep asserts the furniture pattern never appears in
`extract_parties_layered().parties`.
