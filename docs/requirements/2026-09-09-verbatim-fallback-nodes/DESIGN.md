# Design: fallback nodes stay on the graph, honestly labeled

**Date:** 2026-09-09
**Requirements:** `REQUIREMENTS.md` in this folder.

## Current architecture, as it actually exists in `src/` today

Read directly from `src/document_profile.py` and `src/casemap_pipeline.py` (not the
pre-governance handoff doc, which describes the target design — this section is what
is really there right now):

- **Party extraction** (`document_profile.extract_parties_layered`) already has the
  fallback this requirement builds on: **Tier 4.5** (`extract_cause_title_block`)
  returns a `TitleBlock` (`text`, `line_start`, `line_end`, `anchor_line`, `reason`)
  when no tier can confidently parse party names, and `PartyResult.title_block` carries
  it. The tier is stamped `tier4b_title_block`, confidence `"block"`. This already is
  "show the section, don't guess the names" — it exists, unmodified, today.
- **What does *not* exist today:** nothing consumes `PartyResult`/`TitleBlock` and
  turns it into a graph node. The Case Symbol Table (`case_symbols.py`, stage [4] in
  `docs/spec/ARCHITECTURE.md`) is the component that would normally do that, and it is
  **not present in this working directory** (`HANDOFF.md` §6 already flags this).
  Today's graph nodes come from an entirely separate path:
  `casemap_pipeline.detect_events()`, which emits one event per **keyword hit**
  (dates/amounts/provisions found near entities within a section), independent of
  whether party extraction succeeded for that section.
- **Graph node shape** (`events: list[dict]`, consumed by `build_inverted_index`,
  `generate_candidate_pairs`, `score_pair`, `sparsify_and_cluster`, `to_react_flow`):
  each event needs `type`, `document_id`, `section_label`, `section_text`,
  `linked_entities` (list of entity ids), `linked_date` (`{"iso": ...}` or `None`),
  `linked_amount` (`{"raw": ...}` or `None`), `polarity`, `sources` (list of
  `{document, page, char_start, char_end, text, section}`).

## What this design actually adds

A new function, `party_result_to_fallback_event()` (proposed name, not yet written in
`src/`), that:

1. Takes a `PartyResult` where `tier in ("tier4b_title_block", "tier5_none")` **or**
   a mandatory-ML result stamped `DEGRADED_*` (`opennyai_bridge.py` / the merge logic
   in `document_profile.extract_parties_hybrid`), plus the document id and offsets.
2. If there's a `TitleBlock`, its `.text` is the span; otherwise (tier5, no block
   located either) there is nothing to build a node from — this design does not force
   a node into existence where the pipeline has no located text region at all.
3. Runs the **existing** deterministic extractors (`casemap_pipeline.extract_deterministic`,
   or the mandatory NER model's own DATE/STATUTE/PROVISION/CASE_NUMBER labels) over
   just that span — never the whole document — to harvest best-effort entities. This
   reuses existing extraction code; it does not invent a second extraction path.
4. Returns an event-shaped `dict` with `type="fallback_party_block"`,
   `linked_entities`/`linked_date`/`linked_amount` populated from step 3 (empty/`None`
   where nothing was found — never guessed), `polarity="NEUTRAL"`, and a new
   `confidence` key (`"block"` or `"degraded"`, taken straight from the existing tier
   string) that `to_react_flow` and `build_evidence_card` must render distinctly (per
   `FORBIDDEN.md` §E15/G1 — this cannot look like a clean node).
5. This dict is appended to the same `events` list that `detect_events` produces, so
   `build_inverted_index` → `generate_candidate_pairs` → `score_pair` →
   `sparsify_and_cluster` → `to_react_flow` need **zero changes** — FR4 is satisfied by
   construction, not by a parallel code path.

## What the POC (this session) actually tests

Before touching `src/` at all, the POC in `temp/2026-09-09-verbatim-fallback-poc/`
does the following against `testdata/`, using the **real** `document_profile.py` and
`casemap_pipeline.py` functions imported directly (both have only lazy, gracefully-
degrading heavy imports — see their own `try/except ImportError` patterns — so they
run standalone without the full dependency set installed):

1. Run `extract_parties_layered()` for real on every test document.
2. For every document that lands on tier 4.5/5, or where the already-recorded
   `en_legal_ner_sm` run (`results_en_legal_ner_sm.json`) shows unstable role labels
   for the same name, build the proposed fallback event by hand (the real function
   doesn't exist in `src/` yet — the POC script has a local copy of the logic to
   validate the shape and the "does this actually improve graph coverage" question
   before it's worth writing into `src/`).
3. Run the real `build_inverted_index`/`generate_candidate_pairs`/`score_pair`/
   `sparsify_and_cluster`/`to_react_flow` unmodified, with fallback events mixed in
   alongside whatever `detect_events` already finds, and report: how many additional
   nodes appear, whether they got any edges, and what their evidence card looks like.

## Confirmed by the POC (see `POC_RESULTS.md`)

- **Fallback-node entities must go through `casemap_pipeline.normalize_entities()`
  before scoring, not the raw NER label text.** The edge-formation supplementary test
  found two mentions of the same person ("Sunil Kumar Gupta" vs "SUNIL KUMAR GUPTA")
  failed to connect purely on case difference — exactly the class of bug
  `normalize_entities()` (BUG-5/BUG-7) already exists to fix elsewhere in the
  pipeline. `party_result_to_fallback_event()` must call it, not skip it.

## Open questions for after the POC, before `TASKS.md`

- Whether `confidence` needs to be a new `events[i]` key (as sketched above) or should
  reuse the existing `DEGRADED_*` tier-string convention directly, to avoid two
  parallel confidence vocabularies.
- Whether fallback events should be excluded from `same_doc_bonus`-style scoring
  boosts that assume a resolved party identity, since a fallback node's "identity" is
  just a text span.
- Whether this should wait for `case_symbols.py` to actually exist, or is independently
  useful without it (current read: independently useful, since `detect_events` already
  doesn't depend on `case_symbols.py` either).
