# FORBIDDEN — the mistakes we will never repeat

> Every rule here is a **scar** — a specific mistake made in an earlier attempt at this
> problem, or a wrong turn caught while designing this one. This list is the project's
> immune system: if a change would do any of these, it is **wrong no matter how good it
> looks.** Read alongside `THESIS.md` and `HEART.md`; `AGENTS.md` requires reading this
> file first, before anything else.

---

## A. Process scars — never repeat these regardless of domain

1. ❌ **Never let the outcome select.** A change, parameter, or conclusion chosen because
   it made a result look better *after seeing the result* is selection-by-outcome — the
   single most common way research and engineering projects fool themselves. The outcome
   may *judge* a proposal; it may never *pick* the proposal.
2. ❌ **Never write a mechanism/justification after seeing the result and present it as
   the reason.** A plausible story invented post-hoc is not evidence — it is narrative
   fallacy wearing evidence's clothes.
3. ❌ **Never make a change without a stated reason that existed *before* you saw whether
   it worked.**
4. ❌ **Never treat "this didn't work" as a failure to hide.** A negative, honestly
   recorded, is a valid and valuable outcome. Findings are never deleted.
5. ❌ **Never edit a past `CHANGELOG.md` or `FINDINGS.md` entry to match what you know
   now.** Append a new entry with a banner pointing at the old one instead.

## C. Scope — never widen without an explicit, dated owner decision

11. ❌ No LLM (generative model) may ever generate, paraphrase, or infer party names,
    dates, amounts, provisions, events, or graph edges in the extraction/graph core —
    only select verbatim spans that validate against source text with char offsets.
    OpenNyAI's Legal NER is an extraction/labelling model, not generative, and is exempt;
    any future model added to the core must be extraction/labelling only, never
    generative, and this decision requires an explicit dated owner decision to change.

## D. Record-keeping

12. ❌ **Never make a change without appending to `CHANGELOG.md` and updating
    `STATUS.md`** as part of the same change.
13. ❌ **Never let a finding exist only in a chat reply, a scratch script, or a temp
    file.** It must be written to `FINDINGS.md` or it did not happen.
14. ❌ **Never take a dependency on, or import from, another codebase without recording
    it.** This project depends on external code (OpenNyAI `en_legal_ner_sm`/`trf`
    pipelines, spaCy, PyMuPDF, PaddleOCR/Surya/Tesseract, rapidfuzz, dateparser,
    sentence-transformers) — record any new external dependency taken on in
    `CHANGELOG.md` when added.

## E. Domain scars — inherited from CaseMap's own build history

> These are real, already-paid-for lessons from the 26-bug ledger in
> `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` §4 and `docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md`. Read the full
> ledger before "fixing" something that looks broken — it may already have a documented
> reason. Do not re-litigate these without new evidence.

15. ❌ **Never let OCR-damaged or low-confidence input produce a confidently-labelled
    result.** BUG-24: OCR garbage (`REP0RTA8LE`, `1N THE 5UPREME C0URT`) was once
    extracted as a party at *high* confidence. A **confidently wrong** result is a worse
    failure than an honest "no parties found, here's why" — this is the single worst
    failure mode this product can produce. Every fallback ladder (OCR, structure,
    parties) must terminate in an honest low/none-confidence result, never a confident
    guess.
16. ❌ **Never make OpenNyAI's Legal NER optional / "try ML, fall back to regex."** It is
    a mandatory layer that always runs, combined with (not superseded by) the
    deterministic `CASE_TYPE_ROLES` refinement. `load_opennyai_ner()` raises by default
    if the model isn't installed — do not quietly make it optional again without an
    explicit, dated owner decision.
17. ❌ **Never trust a fix or claim of correctness against synthetic test data alone.**
    Every synthetic test group passed before real documents were tried, and real
    documents (`real_docs/`, `real_pdfs/`) still found 11 new bugs across two rounds.
    Real documents are the only valid test oracle for this project — see `THESIS.md` §5.
18. ❌ **Never assume plain-text (`.txt`) test coverage exercises the OCR path.** BUG-26:
    OCR text reconstruction silently discarded all line breaks, and this was invisible
    for multiple sessions because every prior dry run used `.txt` files, never a
    genuinely rendered/rasterised PDF. Any claim about OCR-path correctness must be
    verified against `real_pdfs/`, not `real_docs/`.

---

**The one-line test for any proposed change:** *Did a reason pick this, or did the
outcome? Is it checked by something that can't be fooled by the person proposing it? Can
it be reproduced from what's written down?* If any answer is wrong, don't make the change
yet — write down why first.

<!-- As real mistakes happen in this project, append new numbered scars here. Do not
     invent domain-specific scars that haven't actually occurred — that turns this file
     into generic advice instead of an honest incident log. -->
