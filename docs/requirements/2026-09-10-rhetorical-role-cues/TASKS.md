# Tasks: rhetorical-role cues (after F-7 POC fixes)

## T1 — Cue table + match_cue in `src/rhetorical_roles.py`

Remove `"in the case of"`. Fuzzy match for cues ≥ 16 chars (`rapidfuzz.partial_ratio`).
PRECEDENT does not carry forward.

## T2 — testdata validation

Doc 01: no carried_forward PRECEDENT poison. Doc 03: FACTS matches "facts of this case".
Doc 21: ARGUMENTS/ANALYSIS still fire.
