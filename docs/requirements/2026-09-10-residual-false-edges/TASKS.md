# Tasks

## T1 — Exclude [0, title-block-end) plus furniture lines

**Acceptance:** none of the 24 leftover connectors (`THE SUPREME COURT OF INDIA`,
`AIR 20xx SUPREME COURT`, `R. Subhash`) are emitted by `extract_entities()` on
`testdata/` 03, 05, 06, 17, 19, 22 (the documents that produced those edges).

## T2 — Reporter-citation filter

**Acceptance:** an entity whose text matches `AIR` + year is not returned.

## T3 — 22-doc re-run

Same protocol as header-noise T4 (`similarity_fn=0`). False cross-document edges
at or near 0; 09/21/22 correct edges do not fall below 14.
