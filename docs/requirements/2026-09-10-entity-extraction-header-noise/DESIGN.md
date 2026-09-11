# Design: skip header regions before generic entity extraction

**Date:** 2026-09-10
**Requirements:** `REQUIREMENTS.md` in this folder.

## The fix (FR1), concretely

`extract_entities(text, offsets, ...)` currently runs on the full document text. The
change: compute the header/cause-title region first (reusing
`document_profile.extract_cause_title_block(text)`, which already returns a
`TitleBlock` with `line_start`/`line_end`), and exclude that line range before
running spaCy NER — pass `extract_entities()` the body text only, or filter returned
entities whose `span` falls inside the header's char range (computed from
`line_start`/`line_end` via the same line-to-offset logic `document_profile.py`
already has internally for `TitleBlock`).

**Why this is expected to fix categories (2) and (3), not just suppress them:** the
malformed multi-line grabs and truncated fragments found in `FINDINGS.md` F-8's
addendum all come from header/party-listing text specifically (cause titles, bench
listings, "Versus" blocks) — exactly the region `extract_cause_title_block` already
knows how to locate. Running generic NER only on body prose (ordinary sentences)
should stop spaCy from ever seeing the malformed multi-line/tabular text that
produces these artifacts in the first place.

**Caveat, stated up front:** `extract_cause_title_block` returns `None` when no
title-block region is found (tier 5 in `document_profile.extract_parties_layered`'s
ladder) — in that case, FR1 has nothing to exclude, and only FR2's stoplist applies.
This is expected and fine; it's the same graceful-degradation principle the rest of
the codebase already follows.

## FR2's stoplist

```python
GENERIC_ENTITY_TEXT = {
    "court", "the court", "high court", "the high court",
    "sessions court", "the sessions court", "supreme court", "the supreme court",
    "versus", "order", "notice", "judgment", "appeal",
    "justice", "adv", "slp", "anr", "union of india",
}
```

Directly copied from `temp/2026-09-10-fact-nodes-poc/poc_fact_nodes.py`'s
`GENERIC_ENTITY_TEXT`, extended with `justice`/`adv`/`slp`/`anr`/`union of india`
found in the full 22-document validation (`FINDINGS.md` F-8 addendum). Applied as a
post-filter in `normalize_entities()` or at the call site, same pattern the POC used
— case-insensitive exact match on stripped entity text, scoped to `PERSON`/`ORG`/
`GPE` labels (not `MONEY`, which doesn't have this noise class).

## What FR3's regression test actually checks

The 7 genuine matches from F-8's addendum: `Bank of Baroda`, `The Bank of Baroda`,
`National Company Law Tribunal`, `Khursheed Anwar`, `Kumar Gupta`,
`Khursheed Anwar & Anr`, `Cygnus Splendid Ltd. & Ors` — all real party/institution
names within the genuine 09/21/22 connected bundle. None of these should ever be
excluded by FR1 (they're not header-region-only mentions — they recur in body prose
too) or FR2 (none match the stoplist). If any of them stop matching after the fix,
that's a regression, not an acceptable tradeoff.
