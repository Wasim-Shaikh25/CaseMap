# Requirements: deterministic rhetorical-role tagging (facts/issues/arguments/analysis/ruling)

**Date:** 2026-09-10
**Read first:** `FORBIDDEN.md`, `AGENTS.md`, `THESIS.md`, `docs/spec/SCOPE.md`.
**Supersedes the direction of:** `FINDINGS.md` F-6 (the `opennyai` rhetorical-role
classifier — real API exists, but blocked on this machine by an unmaintained
transitive dependency requiring an old Rust compiler that doesn't compile against a
modern Rust toolchain either; abandoned as the wrong problem to chase, not because a
non-generative classifier was disallowed — it isn't, see below).

## Problem

The owner asked for a "full tree" breakdown of a document — prayers, issues,
questions of law, facts, arguments, ruling — rather than the sparse handful of nodes
`casemap_pipeline.detect_events()` produces (it only fires on 6 narrow event-keyword
categories: payment, termination, notice, agreement, order, filing).

Two different sub-problems got conflated during research and need to stay separate:

1. **Petition-side structural headings** (`PRAYER`, `GROUNDS`, `QUESTIONS OF LAW`,
   `SYNOPSIS`, etc.) — `casemap_pipeline.ANNEXURE_PATTERN` (line 325) **already**
   matches these as standalone heading lines. Nothing to build here; the gap is having
   real petition/pleading test documents (`testdata/` is judgments, which never carry
   these headings) — separate from this requirement.
2. **Judgment-prose rhetorical structure** (facts/issues/arguments/analysis/ruling as
   labels on ordinary prose paragraphs, with no literal heading) — this is what this
   requirement covers.

## Why not the real OpenNyAI rhetorical-role model

Not a governance objection — the model is a sentence classifier, not generative, and
would be as compliant with `FORBIDDEN.md` §C as `en_legal_ner_sm` already is. It's
blocked by an unmaintained 2019 dependency chain (`pytorch-transformers` → an old Rust
`tokenizers` crate) that fails to compile on this machine even with a period-matched
old Rust toolchain installed (see `FINDINGS.md` F-6). Revisit only if that blocker is
independently resolved (e.g. WSL/Linux, or a modern reimplementation is found) — not
in scope here.

## Goal

A deterministic, keyword-cue-based rhetorical-role tagger — same mechanism
`detect_events()` already uses safely (`EVENT_KEYWORDS` phrase matching), extended to
paragraph-level role classification instead of point-in-text event hits. No ML
model, no new dependency.

## Non-goals

- **Not a claim of matching the real classifier's accuracy.** Phrase cues will miss
  paragraphs that don't use standard legal phrasing. This is explicitly a coarser,
  lower-cost approximation, not a replacement for a trained model if one becomes
  available later.
- **Not the petition-heading problem** (`ANNEXURE_PATTERN` already covers it — see
  above). Do not duplicate that logic here.
- **Not a change to `detect_events()`'s existing 6 event types** — this is a new,
  separate function producing a different kind of node (a role-tagged paragraph span,
  not a keyword-hit event).

## Functional requirements

1. **FR1** — Segment a document's text into paragraphs (reuse existing paragraph/line
   splitting conventions already used elsewhere in `document_profile.py`/
   `casemap_pipeline.py`, don't invent a new one).
2. **FR2** — For each paragraph, match against a phrase-cue table (Facts, Issues,
   Petitioner's Arguments, Respondent's Arguments, Analysis/Reasoning, Precedent,
   Ruling/Conclusion) and assign the first/strongest matching role.
3. **FR3** — When no cue matches a paragraph, carry forward the previous paragraph's
   role (rhetorical roles are contiguous blocks in real judgments, not isolated
   per-sentence flips) rather than leaving it untagged or defaulting to a fixed role.
4. **FR4** — Every tagged span keeps char-offset provenance (`THESIS.md`'s core
   promise) — never a paraphrase, always the literal paragraph text.
5. **FR5** — Confidence must be visibly lower than a trained-model tag would be,
   consistent with `FORBIDDEN.md` §E15/G1 — this is a heuristic, and downstream
   consumers must be able to tell.

## Acceptance / validation

POC against real `testdata/` documents first (`FORBIDDEN.md` §E17 — real documents
are the oracle), reviewed for whether the role sequence looks plausible on an actual
judgment before any `src/` change is proposed.
