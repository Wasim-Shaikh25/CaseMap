# Tasks: fallback nodes stay on the graph, honestly labeled

**Date:** 2026-09-09
**Requirements/Design/POC:** `REQUIREMENTS.md`, `DESIGN.md`, `POC_RESULTS.md` in this
folder. Read all three before starting — this task list assumes their conclusions.

Every task below is scoped to what the POC actually validated. Do not widen scope
mid-implementation without a new dated note here.

## T1 — `party_result_to_fallback_event()` in `document_profile.py`

Implements `DESIGN.md`'s proposed function. Input: a `PartyResult` where
`tier in ("tier4b_title_block", "tier5_none")` and `title_block is not None`, plus
`document_id` and the section's page offsets (same offsets `extract_deterministic`
already takes). Output: an `events[i]`-shaped `dict` — see `DESIGN.md` for the exact
keys. Must call `casemap_pipeline.extract_deterministic()` on `title_block.text` only
(never the whole document) for `linked_entities`/`linked_date`/`linked_amount`.

**Acceptance:** unit test against at least one synthetic tier-4.5 document and one
synthetic tier-5 (no-block) document — tier-5 with no block must return `None`, not an
empty node (`DESIGN.md` point 2).

## T2 — ML-layer role-instability trigger in `document_profile.extract_parties_hybrid`

A second, separate trigger from T1: when the mandatory ML layer's merged output tags
the same normalized name with more than one role across mentions in a document (the
F-2/F-3 pattern), route that document/section through the same
`party_result_to_fallback_event()`-shaped output, stamped with a distinct confidence
value (not `tier4b_title_block`/`tier5_none` — those are regex-ladder tiers; use
something like `"ml_role_unstable"`, matching what the POC scripts used ad hoc).

**Acceptance:** re-run against `testdata/01`, `12`, `16`, `17` (the 4 documents F-3
found this pattern in) and confirm all 4 produce a fallback event with this stamp.

## T3 — Call `normalize_entities()` on fallback-node entities before scoring

**This is not optional** — `POC_RESULTS.md`/`DESIGN.md` both found real edge
formation depends on it (the ALL-CAPS vs title-case miss between `testdata/21` and
`testdata/22`). `party_result_to_fallback_event()`'s `linked_entities` must be passed
through `casemap_pipeline.normalize_entities()` (type-scoped) before being placed in
the returned dict — not left as raw NER label text.

**Acceptance:** re-run `temp/2026-09-09-verbatim-fallback-poc/poc_edge_formation_test.py`'s
scenario (docs 09/21/22 + the negative control) through the real, updated code path
and confirm doc 22 now connects to 09/21 where it didn't before.

## T4 — Confidence rendering in `to_react_flow()` / `build_evidence_card()`

Per `FORBIDDEN.md` §E15/G1: a fallback node must be visibly distinct from a clean
node, not just internally tagged. Extend `to_react_flow`'s node `data` and
`build_evidence_card`'s output to surface the `confidence` field from T1/T2 so a
fallback node cannot be mistaken for a resolved one downstream (UI work, stage [6],
is not yet built — this only needs the data to be present in the JSON shape, not a
UI change).

**Acceptance:** `to_react_flow()` output for a graph containing at least one fallback
node has that node's `data.confidence` (or equivalent key) populated and distinct
from a clean node's.

## T5 — Wire into `poc_run.py` / the real pipeline run

Once T1-T4 pass their acceptance checks in isolation, wire `party_result_to_fallback_event()`
into the actual per-document pipeline flow (`document_profile.extract_parties_hybrid`
→ event list → `casemap_pipeline` graph stages), so fallback nodes appear in a real
`poc_run.py` run against `testdata/`, not just a standalone POC script.

**Acceptance:** `python scripts/poc_run.py testdata --allow-degraded` (or equivalent)
produces a `poc_graph.json` containing fallback nodes for docs 01/12/16/17, and an edge
between 09/21/22.

## Explicitly deferred (not in this task list)

- Regex-ladder tier 4.5/5 trigger validation against real OCR-damaged input —
  `POC_RESULTS.md` flagged this as still unexercised. Needs `real_pdfs/` or equivalent
  (`HANDOFF.md` §6), which doesn't exist in this working directory yet. Track
  separately once that corpus exists — do not block T1-T5 on it, since T1's code path
  is exercised the same way regardless of *why* the tier fired.
- React Flow / PDF.js UI rendering of fallback nodes (stage [6] generally isn't built
  yet, per `HEART.md` — out of scope here, T4 only prepares the data).
