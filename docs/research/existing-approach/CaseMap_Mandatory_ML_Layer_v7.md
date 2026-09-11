# CaseMap — Mandatory ML Layer Integration (v7)

Answers the directive: OpenNyAI's legal NER is no longer optional tier-0. It is a **required** processing step, combined with (not falling back from) the deterministic layer. Building and testing it surfaced a real bug that predates this session entirely.

**New:** `opennyai_bridge.py`, `test_opennyai_bridge.py` · **Modified:** `document_profile.py`, `poc_run.py`, `casemap_pipeline.py`

---

## 1. What "mandatory" means, precisely

Not "try ML, fall back to regex if unavailable." Two layers, both required, results merged:

- **Layer 1 (mandatory):** OpenNyAI ML NER finds party **names** and a rough PETITIONER/RESPONDENT-style **side**. Trained on 46,545 hand-annotated entities across many Indian courts — generalises to registries this codebase has never regex'd for.
- **Layer 2 (mandatory):** the existing deterministic `CASE_TYPE_ROLES` mapping refines that generic side into the **precise role** — Plaintiff/Defendant for a suit, Financial Creditor/Corporate Debtor for insolvency. The ML label set doesn't know what a commercial suit is; this layer always runs on ML output, never skipped.

`load_opennyai_ner()` is called **eagerly**, before any PDF is touched. By default it **raises** `ModelNotAvailableError` with the exact install command if the model can't load — verified live:

```
[+] loading OpenNyAI legal NER ('sm') -- MANDATORY layer ...
ModelNotAvailableError: OpenNyAI legal NER model ('sm') is REQUIRED and could
not be loaded ... Install it with: pip install https://huggingface.co/...
```

The failure happens **before processing the first PDF** — no wasted OCR or structure-detection work on a run that can't complete.

An explicit `allow_degraded=True` (`--allow-degraded`) escape hatch exists for local development before the model is installed. It prints a loud stderr banner **once** (fixed — see §3) and stamps every downstream result `DEGRADED_*` so it can never be mistaken for the real pipeline's output.

---

## 2. Honesty about what was and wasn't tested

`huggingface.co` isn't in this sandbox's network allowlist, so **the real model weights were never loaded here.** What I could and did do: install spaCy itself (it's on PyPI, unblocked), and build tests against spaCy's **real** `Doc`/`Span`/`Token` API with a hand-written entity **source** standing in for the model's forward pass.

```python
class FakeOpenNyAINLP:
    """nlp(text) -> real spacy.tokens.Doc via doc.char_span() + doc.set_ents().
    FAKE: which spans get proposed. REAL: everything that reads them —
    ent.text, ent.label_, ent.start_char, ent.end_char, and every line of
    opennyai_bridge.py / extract_parties_hybrid() consuming them."""
```

This proves the **glue code**: offset handling, role-merging, mandatory-raise behaviour, degraded-mode stamping. It cannot prove the real model's extraction **accuracy** — that's only verifiable once you `pip install` the actual weights.

**20/20 tests pass**, six groups:

| Group | Proves |
|---|---|
| A | `extract_parties_ml()` reads real spaCy `Doc.ents` correctly, preserves offsets |
| B | Role refinement: ML's generic `PETITIONER`→`RESPONDENT` becomes `Plaintiff`→`Defendant` for a commercial suit |
| C | `load_opennyai_ner()` raises when required; returns `None` only with `allow_degraded=True` |
| D | Degraded-mode result is stamped `DEGRADED_*`, deterministic ladder still finds the real parties |
| E | ML runs but finds nothing → falls through to the full 5-tier ladder, **not** stamped degraded (the model was active, just empty on this document) |
| F | Regression: the regex-only ladder is unchanged and still works standalone |

---

## 3. Bugs found building this (glue-layer, not model-layer)

### BUG-25 — repeated load attempts, spammed banner

First wiring called `load_opennyai_ner()` again inside `extract_parties_hybrid()` every time `nlp=None` was passed, even when the caller (`poc_run.py`) had already resolved that the model was unavailable — one warning banner per document instead of one per run.

**Fix:** a sentinel default (`_UNSET`) distinguishes "caller didn't pass `nlp`" (auto-load) from "caller explicitly passed `None`" (already resolved, use as-is). `poc_run.py` now loads once and passes the result to every document.

### BUG-26 — OCR text reconstruction discarded line breaks (found via this integration, not caused by it)

While running the mandatory layer end-to-end against real scanned PDFs, `t5_crim_scanned.pdf` — the rasterised version of a document that extracts perfectly as plain text — returned **zero parties**. Investigating why surfaced a bug that predates this session:

```python
# casemap_pipeline.py, _ocr_tesseract() — BEFORE
return {"text": " ".join(parts), "words": words}
```

Every word from every line joined with a single space. The entire cause title collapsed into one fused line:

```
REPORTABLE IN THE SUPREME COURT OF INDIA ... SHAILESH KUMAR .. Appellant
VERSUS STATE OF MAHARASHTRA & ANR. .. Raspondents JUDGMENT ...
```

`is_versus_line()` requires `VERSUS` to be the **entire content of its own line** — by design, since a standalone separator line is what distinguishes a real cause title from the word "versus" appearing in body prose. With no line breaks at all, this never matched, and `BODY_START_RE`, TOC dot-leader detection, and every other line-based rule in `layout_structure.py` and `document_profile.py` were silently degraded on **every real OCR'd document** — not just this one. `layout_structure.py`'s own `lines_from_ocr_words()` was unaffected (it does its own row-grouping internally), but the plain `text` field everything else reads was flat.

**Fix:** extracted the row-grouping logic already proven correct in `layout_structure.lines_from_ocr_words()` into a shared `_words_to_lines_text()`, applied to both the Tesseract and Paddle paths:

```python
# AFTER — grouped by y-coordinate into rows, joined with \n
REPORTABLE
IN THE SUPREME COURT OF INDIA
CRIMINAL APPELLATE JURISDICTION
...
SHAILESH KUMAR .. Appellant
VERSUS
STATE OF MAHARASHTRA & ANR. .. Raspondents
```

**Verified before/after on the same real PDF:**

```
BEFORE:  tier=tier5_none      conf=none
AFTER:   tier=tier1_cause_title  conf=high
  A | SHAILESH KUMAR -> Appellant (explicit)
  B | STATE OF MAHARASHTRA & ANR. Raspondents -> Respondent (case_type)
```

**One residual, logged rather than hidden:** the recovered role for side B says `Respondent` via `case_type` inference rather than `explicit`, because OCR rendered "Respondents" as "**Ra**spondents" (a/e swap) and `ROLE_MARKER_RE` expects exact spelling, so it wasn't recognised or stripped from the name. Minor — the party and side are still correct — but a legitimate remaining gap, not swept under the rug.

This bug was invisible in every prior dry run because those used **plain `.txt` files** — real content, but never actually OCR'd. The mandatory-layer work forced a genuine end-to-end run against rendered PDFs for the first time, which is exactly why it surfaced now and not three sessions ago.

---

## 4. Result: all 6 real PDFs, before vs after this session

| Document | Before (start of session) | After |
|---|---|---|
| t1_jaggo_bookmarked.pdf | tier1, high | tier1, high (unchanged) |
| t2_delhibail_headings.pdf | tier1, high | tier1, high (unchanged) |
| t3_jain_flat.pdf | tier1, high | tier1, high (unchanged) |
| t4_nclt_separators.pdf | tier1, high | tier1, high (unchanged) |
| **t5_crim_scanned.pdf** | **tier5_none** | **tier1, high** ← BUG-26 fix |
| **t6_jet_scanned_headings.pdf** | tier1, high (was already OK — digital text path, not affected) | tier1, high |

Full regression: `test_logic.py`, `test_layout.py`, `test_profile_symbols.py`, `dryrun_real.py`, `test_opennyai_bridge.py` — **all pass.**

---

## 5. Rhetorical-role model — honest status

Also meant to be mandatory, per the instruction. Built the loader with the same eager-raise design (`load_rhetorical_role_model()` in `opennyai_bridge.py`), but I could not find a confirmed one-line `spacy.load(...)`-style API for it the way the NER model has documented usage. The baseline lives in `Legal-NLP-EkStep/rhetorical-role-baseline` on GitHub with its own inference script, not a pip-installable package. The function currently **always raises**, naming this gap explicitly, rather than pretending to a working integration I haven't verified exists in that form. This is a stub with the right shape, not a working mandatory layer yet — confirm the repo's actual inference entrypoint before wiring it for real.

---

## 6. What to do next

1. **Install the real model and re-run `poc_run.py` without `--allow-degraded`.** Everything is wired for this — it's the one thing this sandbox structurally cannot do.
2. Confirm the exact label casing (`PETITIONER` vs `Petitioner` vs other) against the loaded model — `PARTY_LABELS_TO_SIDE` in `opennyai_bridge.py` is transcribed from documentation, not checked against live weights.
3. Decide on `sm` vs `trf` — `sm` is wired as the default; `trf` is higher-F1 (91.08 reported) but slower, worth an A/B on your real bundle.
4. Confirm the rhetorical-role model's real inference entrypoint before treating §5 as done.
5. Fix the `Raspondents` role-marker gap from §3 if it recurs on your real scan corpus — likely worth a small OCR-tolerant probe on `ROLE_MARKER_RE` similar to the one already built for party-name rejection.
