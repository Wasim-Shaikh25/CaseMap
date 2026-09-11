# Design: exclude preamble prefix, not only the versus block

**Date:** 2026-09-10

`extract_cause_title_block` returns a *versus-centred* region. Caption lines
above that region (`IN THE SUPREME COURT OF INDIA`, `Equivalent citations:`,
`Bench:`) are still header. Residual F-8 edges were 100% from that leftover
prefix.

Change `_body_segments_excluding_title_block` so the excluded range is
`[0, header_end)` where `header_end` is the max of:

- char end of `TitleBlock.line_end` (if a block exists), and
- char end of the last furniture line among the first 40 lines matching
  `Equivalent citations|Author|Bench|REPORTABLE|Source:`.

Reporter citations: `_is_reporter_citation(text)` if `\bAIR\s+\d{4}\b` or
`AIRONLINE` — applied in `extract_entities` / `normalize_entities` next to
`_is_generic_entity`. Do **not** treat `National Company Law Tribunal` as a
reporter or as a bare "court" stoplist hit (FR3).

Add `"the supreme court of india"` to `GENERIC_ENTITY_TEXT` as the missing
sibling of the existing `"the supreme court"` exact match — backup only;
FR1 is the real fix.
