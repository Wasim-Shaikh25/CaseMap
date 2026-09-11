# POC results: fallback nodes stay on the graph

**Date:** 2026-09-09
**Script:** `temp/2026-09-09-verbatim-fallback-poc/poc_fallback_nodes.py` (uses the
real `document_profile.extract_parties_layered` and `casemap_pipeline` graph
functions, unmodified — see the script's own docstring for exactly what's real vs.
simplified).
**Raw output:** `temp/2026-09-09-verbatim-fallback-poc/poc_results.json`.

## Honest headline: the trigger fired less than expected, for a real reason

Against all 20 `testdata/` documents, the real deterministic ladder
(`extract_parties_layered`) resolved **every single one** at tier 1 (15 docs) or
tier 4 (5 docs) — **zero landed on tier 4.5 ("verbatim block") or tier 5 ("no
parties")**. That's not the ladder being weak; it's the opposite: on clean, digitally-
sourced judgment text (no OCR damage, no scanned-PDF artifacts), the deterministic
cause-title/inline-versus detection this project already built is robust. This
document set does not exercise the failure mode this requirement is designed for —
that failure mode is specifically OCR/layout damage (`FORBIDDEN.md` §E18, BUG-26), and
`testdata/` has none of that (see `testdata/README.md` — plain text, not scanned
PDFs).

**The trigger that did fire, 4/20 times, was the mandatory ML model's role
instability** (the same F-2 finding from the `en_legal_ner_sm` run: the same person's
name tagged both `PETITIONER` and `RESPONDENT` in different mentions). Fallback nodes
were built for those 4 documents from a representative excerpt, carrying whatever
DATE/STATUTE/PROVISION/CASE_NUMBER entities the model found in that excerpt.

## The mechanism itself checks out

The 4 fallback events were built in the exact `events[i]`-dict shape
`casemap_pipeline`'s real, unmodified functions expect, and
`build_inverted_index` → `generate_candidate_pairs` → `score_pair` →
`sparsify_and_cluster` → `to_react_flow` ran over them with **zero special-casing** —
confirming `REQUIREMENTS.md` FR4 is achievable exactly the way `DESIGN.md` proposed.

## The honest gap: edge formation wasn't meaningfully testable here

The graph came back **4 nodes, 0 edges**. That is not a failure of the scoring logic
— it's because `testdata/`'s 20 documents are 20 unrelated public judgments from
different cases entirely (a murder appeal, a consumer dispute, a tax appeal, a
succession suit — no shared parties, dates, or case numbers by construction). There
was never a reason for these 4 specific nodes to connect. **This POC cannot answer
"do fallback nodes actually get useful edges inside a real case bundle"** — that needs
multiple documents that are actually part of the same matter (e.g. a bail application
+ the FIR + the charge sheet it's about), which is exactly what `real_docs`/`real_pdfs`
(referenced throughout `CaseMap_AGENT_HANDOFF.md`, still not present in this working
directory per `HANDOFF.md` §6) would provide and `testdata/` does not.

## Follow-up: a real connected bundle, and a direct scoring test

The owner asked to get connected test documents before deciding how to proceed. Added
two documents to `testdata/` that are genuinely part of the same matter as the
existing doc 09: `21_insolvency_nclat_khursheed_anwar_v_sunil_kumar_gupta_2025-09.txt`
(same Corporate Debtor "Cygnus Splendid Ltd", same RP "Sunil Kumar Gupta", same
Chairperson Ashok Bhushan — a later NCLAT order in the same CIRP) and
`22_insolvency_sc_khursheed_anwar_v_sunil_kumar_gupta_2025-12.txt` (the Supreme Court
appeal from *that exact* NCLAT order — it names the order's date and case number
verbatim). Re-running `poc_fallback_nodes.py` against all 22 documents: **still zero
fallback triggers** — this bundle also resolves cleanly at tier 1, confirming the
first result wasn't a sampling artifact of the original 20.

Since the trigger genuinely doesn't fire on any available document, edge formation
can't be tested through the trigger path with real data yet. `poc_edge_formation_test.py`
isolates the narrower, still-real question — **given** a fallback node, does entity
overlap actually connect it to related documents — by force-building fallback-shaped
nodes from the 3 bundle documents' cause-title regions (clearly labeled
`confidence: "forced_test_not_a_real_trigger"`, not a claim about when real nodes get
created) plus one unrelated document as a negative control.

**Result: 09 ↔ 21 got a real edge** (`entity_overlap=0.611`, via the shared name
`"Sunil Kumar Gupta"`), and the unrelated control never connected to anything —
correct discriminative behavior. **09/21 did not connect to 22**, and the reason is
itself a useful finding: doc 22's header writes party names in ALL CAPS
(`"SUNIL KUMAR GUPTA"`), an exact-string mismatch against `21`'s title-case
`"Sunil Kumar Gupta"` — this POC does no entity normalization, but the real pipeline's
`casemap_pipeline.normalize_entities()` (the BUG-5/BUG-7 fix, type-scoped fuzzy dedup)
exists precisely to catch this. **This is a real, additional argument for why the
fallback-node design must run its entities through `normalize_entities()` before
scoring, not the raw NER label text** — not previously called out explicitly in
`DESIGN.md`'s open questions, and now added there.

## What this means for next steps

1. **The core mechanism is validated**: fallback events, in the real `events[i]`
   shape, flow through the real, unmodified graph pipeline (FR4) — confirmed twice
   now, including with genuinely connected real documents.
2. **Edge formation is validated, conditionally**: it works when entity text matches
   exactly, and correctly stays silent when documents are unrelated (the negative
   control never connected). It does **not yet** work across formatting variation
   (ALL CAPS vs title case) — that is a known, explained gap, not an unknown one:
   `normalize_entities()` needs to run on fallback-node entities before scoring. This
   must be a stated part of `TASKS.md`, not an afterthought.
3. **The trigger condition (tier 4.5/5, or ML role-instability) has not fired on any
   of the 22 real documents tested**, including a genuinely connected 3-document
   bundle. This is expected — that tier exists for OCR-damaged input, which nothing
   in `testdata/` has (see `testdata/README.md`) — but it means the trigger half of
   this requirement remains validated only in the ML-role-instability case (F-2), not
   the regex-ladder case. A future POC pass against genuinely OCR-damaged text (or
   `real_pdfs/`, once it exists — see `HANDOFF.md` §6) is needed before calling that
   half proven too.
