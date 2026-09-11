# Requirements: recover `case_symbols.py` (stage [4])

**Date:** 2026-09-10
**Read first:** `docs/spec/ARCHITECTURE.md` §1 stage [4], `HEART.md` (tier 1 vs
tier 2), `HANDOFF.md` §6, `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md`
§3 (`case_symbols.py`, 513 lines — file absent here).

## Problem

Stage [4] is specified and `opennyai_bridge.extract_parties_ml` already tries
`from case_symbols import normalize_name` (ImportError fallback today). The
file is not in this working tree. Without it, there is no definition-site /
find-all-references / go-to-definition table for extracted spans.

## Goal

`src/case_symbols.py` implementing the **documented** API:

- `normalize_name` — shared key for party/person strings
- `normalize_amount` / `amount_from_words` — value keys (functions exist for
  callers; **do not** build HEART tier-2 figures-vs-words *cross-check*)
- Symbol table: definition sites, aliases by kind, `go_to_definition()`,
  `find_all_references()`, cross-document merge by canonical key
- Provision keys by act+section **without** act-name inheritance (that is
  HEART tier 2, item in AGENT_HANDOFF §7.2 — out of scope here)

Spans stay verbatim with offsets. No generative model.

## Non-goals

- Act-name inheritance for bare `Section 24` (tier 2).
- Amount figures-vs-words mismatch flagging (tier 2).
- React UI.

## Functional requirements

1. **FR1** — `normalize_name` is importable; `extract_parties_ml` uses it
   (drop the ImportError stub).
2. **FR2** — `SymbolTable.add()` from deterministic rows + entity dicts;
   `go_to_definition(key)` returns the first definition site; `find_all_references`
   returns all sites including other documents.
3. **FR3** — Amount aliases share a numeric key (`₹1,20,00,000` and `Rs. 12000000`
   merge). Provisions share `section` token only unless an act string is in
   the same raw span (no carry-forward of a previous act).
4. **FR4** — Real `testdata/` 09/21/22: shared party names produce one key
   with references in more than one document.

## Acceptance

Unit tests plus a 09/21/22 testdata pass showing `find_all_references` hits
more than one document for at least one genuine bundle name (e.g. Baroda /
Khursheed / Cygnus).
