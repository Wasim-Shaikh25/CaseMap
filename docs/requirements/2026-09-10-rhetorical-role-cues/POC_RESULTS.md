# POC results: deterministic rhetorical-role tagging

**Date:** 2026-09-10
**Script:** `temp/2026-09-10-rhetorical-role-cue-poc/poc_rhetorical_cues.py`
**Raw output:** `temp/2026-09-10-rhetorical-role-cue-poc/poc_results.json`

## Summary

| Document | Paragraphs | Cue-matched | Verdict |
|---|---|---|---|
| `21_insolvency_nclat_khursheed_anwar...2025-09.txt` | 7 | 5 | Correct role sequence |
| `01_criminal_sc_dilip_kumar_sharma_v_mp.txt` | 20 | 3 | Broken — false positive poisoned carry-forward |
| `03_matrimonial_sc_rajnesh_v_neha.txt` | 11 | 0 | No coverage — cue wording too exact |
| `09_insolvency_nclat_singhania_v_bank_of_baroda.txt` | 4 | 0 | Mostly untagged boilerplate (reasonable) |

## The positive case (doc 21)

Produced exactly the right sequence: `ARGUMENTS_PETITIONER` → `ARGUMENTS_RESPONDENT`
→ `ANALYSIS` × 3, matching a human skim of the actual order. This is real evidence
the mechanism (cue table + paragraph carry-forward) works when cue phrasing matches.

## Failure 1 — a too-generic cue caused a false positive that poisoned everything downstream

Doc 01, paragraph 9 (the `HEADNOTE`), matched `PRECEDENT` on the substring
`"in the case of"` — found in `"...conviction under section 303 in the case of
Rohitsingh..."`, ordinary prose meaning "regarding Rohitsingh," not a citation. Because
`tag_paragraphs()`'s carry-forward logic (FR3) has no re-confirmation mechanism, this
single false match locked every subsequent paragraph to `PRECEDENT` — including
`FACTS`, `ANALYSIS`, and eventually a real `ISSUES` paragraph that only broke through
because it had its own distinct cue match.

**Root cause:** `"in the case of"` is common English with two meanings (precedent
citation vs. "regarding X"); the cue table treated it as unambiguous. Needs either
removal or a stricter pattern (e.g. requiring a citation-shaped string — party names
+ "v." + year — nearby).

## Failure 2 — exact substring matching missed real wording variation

Doc 03's actual text: `"In the backdrop of the facts of this case, we considered it
fit to frame guidelines..."`. The `FACTS` cue table has `"the facts of the case"` —
one word off (`this` vs `the`) causes a complete miss. The codebase already has a
proven fix for exactly this class of problem: `document_profile.is_versus_line()`
falls back to `rapidfuzz.fuzz.ratio()` for OCR-tolerant comparison. The same pattern
(fuzzy match above a threshold, not exact substring) should apply here.

## What this means for `TASKS.md`

Not ready to write into `src/` as-is. Two concrete fixes needed first:
1. Remove or tighten cue phrases with a non-legal-writing common meaning (start with
   `"in the case of"`).
2. Replace exact substring matching with fuzzy matching (`rapidfuzz`, same pattern as
   `is_versus_line()`), tuned against a larger sample of real documents than these 4.

Re-run this POC after both fixes before formalizing `TASKS.md`.
