# Requirements: fix generic-NER header-block noise in extract_entities()

**Date:** 2026-09-10
**For:** whoever picks this up next (Cursor or otherwise) — this is a confirmed bug
in existing `src/` code, found via full-corpus validation, not a hypothetical.
**Read first:** `FORBIDDEN.md`, `AGENTS.md`, `FINDINGS.md` F-8 (full addendum — this
requirement formalizes its fix).

## The bug, precisely

`casemap_pipeline.extract_entities()` uses generic spaCy NER (`en_core_web_sm`, not
the mandatory legal-domain `en_legal_ner_sm`) to find PERSON/ORG/GPE/MONEY entities.
Validated against all 22 `testdata/` documents (`FINDINGS.md` F-8 addendum): of 28
entities shared across 2+ documents, only 7 are genuine matches (real parties within
one connected case bundle) — the other **20 are noise**, falling into three distinct
root causes:

1. **Generic institutional/procedural nouns**, near-universal in Indian legal
   writing: `Court`, `High Court`, `Justice`, `Versus`, `Order`, `Notice`, `Adv`,
   `SLP`, `Anr`, `Union Of India` (the last because it's the near-universal
   respondent name in any case against the government — its presence signals
   nothing about whether two cases are actually related).
2. **Malformed multi-line entity extraction** — spaCy sometimes grabs an entire
   header block as one "entity": `"THE SUPREME COURT OF INDIA\nCIVIL APPELLATE
   JURISDICTION\nCIVIL APPEAL"`. Root cause: header/cause-title regions are not
   ordinary prose, and `extract_entities()` runs generic sentence-oriented NER over
   them anyway, without ever consulting the header-region detection the codebase
   already has (`document_profile.extract_cause_title_block`,
   `document_profile.is_versus_line`).
3. **Truncated fragments**: `"Appellant(s"`, `"R. Subhash"`, `"PRINCIPAL"`,
   `"C.A. No"` — likely the same header-region formatting (line wraps, tabular
   party-listing layout) confusing spaCy's tokenizer at line boundaries.

**Why this matters beyond the fact-node POC that found it:** any real multi-document
pipeline run using `detect_events()`'s existing entity-linking, or the graph
construction stage (`build_inverted_index`/`generate_candidate_pairs`/`score_pair`),
inherits this bug today. It is not specific to the dense-fact-node experiment.

## Goal

Reduce false entity-sharing between unrelated documents caused by header-block noise,
without breaking genuine entity matches (verified: `Bank of Baroda`, `Khursheed
Anwar`, `National Company Law Tribunal`, etc. — the 7 real matches found — must still
match after the fix).

## Non-goals

- **Not a fix to `en_legal_ner_sm`** — that's the mandatory legal-domain model
  (F-2), a separate, already-more-accurate extraction path. This requirement is
  scoped to `extract_entities()`'s generic spaCy usage only.
- **Not a rewrite of `normalize_entities()`'s fuzzy-matching logic** — that function
  (BUG-5/7 fix) is working as designed; the problem is upstream, in what gets fed
  into it.
- **Not a hand-maintained stoplist as the only fix.** A stoplist can suppress
  category (1) (the exact 10 words found so far — but there will be more, and a list
  only ever covers what's already been seen). Categories (2) and (3) need the
  architectural fix below, not more list entries.

## Functional requirements

1. **FR1** — Before running `extract_entities()` on a document's text, skip or
   separately handle the header/cause-title region (identifiable via
   `document_profile.extract_cause_title_block()`, already returning a `TitleBlock`
   with `line_start`/`line_end`) so generic NER runs only on body prose, not
   multi-line formatted headers — this is expected to fix categories (2) and (3) at
   the root, not just suppress their symptoms.
2. **FR2** — A short, explicit stoplist (category 1's ~10 confirmed generic terms)
   for whatever header-independent noise remains — case-insensitive exact match on
   the normalized entity text, same pattern this requirement's own POC used
   (`temp/2026-09-10-fact-nodes-poc/poc_fact_nodes.py`'s `GENERIC_ENTITY_TEXT`).
3. **FR3** — The 7 genuine cross-document matches found in F-8's addendum must still
   match after the fix — a regression test, not just a noise-reduction check.

## Acceptance / validation

Re-run `temp/2026-09-10-fact-nodes-poc/poc_fact_nodes.py` (or a real `src/`-wired
equivalent) against all 22 `testdata/` documents after the fix. Target: false
cross-document edges materially below the current 60; the 10 correct bundle edges
(or more, if `normalize_entities()` catches additional genuine matches once noise is
reduced) must not regress.
