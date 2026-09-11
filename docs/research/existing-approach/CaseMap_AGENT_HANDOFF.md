# CaseMap — Agent Handoff Document

**Read this before touching any code.** This project has an unusual number of hard-won constraints baked into it from real testing, not just design preference. Section 0 lists what must not be violated. Everything after is context and detail.

---

## 0. Non-negotiable constraints (read this part twice)

1. **No LLM in the extraction/graph core.** Party names, dates, amounts, provisions, events, and graph edges must never be *generated* — only *selected* (spans that exist verbatim in the source, with char offsets that validate against it). This is the product's entire differentiator: "every fact traces to a source page, nothing is invented." An LLM in the core loop breaks that claim even if it's more accurate. If you're tempted to "just call an LLM to extract parties," don't — that's the exact thing this build spent 26 bugs avoiding. See §2 for why the ML layer that *is* used (OpenNyAI NER) doesn't violate this: it's an extraction/labelling model, not a generative one.
2. **OpenNyAI's Legal NER is MANDATORY, not optional.** Per explicit instruction, it is not a "try ML, fall back to regex" tier. It is a required layer that always runs, combined with (not superseded by) the deterministic case-type role refinement. `load_opennyai_ner()` **raises** by default if the model isn't installed. Do not quietly make it optional again.
3. **Every fallback ladder must terminate, never crash, and never lie.** Three ladders exist (OCR, structure, parties). Each has a final tier that always succeeds (even if the result is "no parties found, here's why"). A **confidently wrong** result (e.g., OCR garbage extracted as a party at high confidence) is a worse failure than an honest "I don't know" — this was BUG-24, the worst bug found in the whole build. Never regress toward confident-wrong.
4. **Real documents are the only valid test oracle.** Every synthetic test group passed before real documents were tried, and real documents still found 11 new bugs across two rounds. Do not trust a fix until it's been run against `real_docs/` (8 real Indian court documents, verbatim from public judgments) and, where OCR is involved, `real_pdfs/` (6 real judgments rendered to PDF, 2 genuinely rasterised with no text layer).
5. **This sandbox cannot reach `huggingface.co`.** Only `pypi.org`, `github.com`/`release-assets.githubusercontent.com`, and a handful of package registries are allowlisted (see exact list in your own network config). The OpenNyAI *model weights* have never been loaded in this environment — only the glue code has been tested, against spaCy's real API with a faked entity source. **The next agent's first job, if it has broader network access, is to actually install and run the real model** and report back whether accuracy matches expectations.

---

## 1. What CaseMap is

A source-grounded, LLM-free-in-the-core visual case-file map for legal document bundles. Upload a folder of case documents (plaints, affidavits, orders, contracts, notices) → the system extracts entities, dates, amounts, provisions, and parties with exact page/character provenance → builds a graph of events and connections across documents → surfaces a timeline, a click-through evidence map, and flagged (never asserted) potential contradictions.

**Origin and positioning (context, not code):** this started as a broader concept called "CaseGraph," which market research (see earlier `CaseGraph_...` docs, not itemised here) concluded was too broad to monetize as a solo-litigator SaaS in India, but viable as a B2B tool for disputes/arbitration teams, or as a hackathon/portfolio project. It was narrowed to "CaseMap" — a tighter, disciplined MVP scope (see `blueprint1.md`, `blueprint2.md` for the original product/boundary docs) for a 72-hour hackathon (ILTN × vibecode.law Vibeathon). The core sales pitch, informed by a real July 2026 Indian Supreme Court ruling treating unverified AI citations as advocate misconduct, is: **"every fact links to a source page; nothing is generated."** Do not build anything that undermines this pitch.

---

## 2. Architecture overview

```
PDFs (bundle)
   │
   ▼
[0] OCR / PAGE INGESTION — 3-tier ladder (casemap_pipeline.py)
   digital text layer / hybrid (merge) / scanned (full OCR: Paddle→Surya→Tesseract)
   │
   ▼
[1] STRUCTURE DETECTION — 5-tier ladder (layout_structure.py)
   PDF bookmarks / layout signals (font+bold+centered+gap, works on OCR too) /
   index-page inference / separator pages / one-section-per-page
   │
   ▼
[2] PARTY EXTRACTION — MANDATORY two-layer (document_profile.py + opennyai_bridge.py)
   Layer 1 (mandatory): OpenNyAI ML NER — party NAMES + rough side
   Layer 2 (mandatory): deterministic CASE_TYPE_ROLES — precise role refinement
   (falls through to a 5-tier regex-only ladder + tier-4.5 "verbatim block" only
    when a document genuinely has no ML/regex-findable parties, or when the ML
    model is running in explicit --allow-degraded development mode)
   │
   ▼
[3] DETERMINISTIC EXTRACTION — dates, amounts (+ words-to-number), provisions,
    case numbers, entities (spaCy generic NER + rapidfuzz normalization)
   │
   ▼
[4] SYMBOL TABLE (case_symbols.py) — Cursor/IDE-style: definition sites,
    aliases, find-all-references, go-to-definition, cross-document merging
   │
   ▼
[5] EFFICIENT EVENT-GRAPH CONSTRUCTION (casemap_pipeline.py)
    inverted-index blocking (avoid O(n²)) → weighted multi-signal scoring
    (entity/temporal/semantic) → top-K sparsify → Union-Find clustering →
    bi-temporal edges (SQLite, no Neo4j) with invalidation semantics
   │
   ▼
[6] OUTPUT — React Flow JSON + evidence cards + PDF.js click-to-source
```

**Why this shape:** each of the three ladders (§ above) was built because a binary "works / doesn't work" check kept breaking on real documents. Each ladder's tiers were earned one real-document failure at a time — see the bug ledger in §4.

---

## 3. File inventory (as of this handoff)

All files live in `/home/claude/` in the current session and were copied to `/mnt/user-data/outputs/` for the user. **Re-verify locations if starting a fresh session.**

### Core pipeline code

| File | Lines | Purpose |
|---|---|---|
| `casemap_pipeline.py` | 918 | OCR (3-tier), deterministic extraction (dates/amounts/provisions/entities), event detection, efficient graph construction (blocking + scoring + Union-Find), bi-temporal SQLite edges |
| `layout_structure.py` | 660 | Structure detection (5-tier ladder), dual feeder (PyMuPDF font signals + OCR word-box geometry → one shared scorer), noise filtering, contents-page detection |
| `document_profile.py` | 1027 | Document-type profiling (court_filing/affidavit/contract/legal_notice/correspondence/financial/court_order/generic), party extraction (5-tier regex ladder + tier-4.5 verbatim block + the new mandatory ML-hybrid path), role cascade, OCR-tolerant matching, name validation |
| `case_symbols.py` | 513 | The Case Symbol Table: definition sites, alias resolution (amounts by value, provisions by act+section, names by normalized key), cross-document entity merging, `go_to_definition()`/`find_all_references()` |
| `opennyai_bridge.py` | 196 | **Mandatory** OpenNyAI Legal NER integration: eager loading, raises by default if model missing, `allow_degraded` escape hatch, offset-preserving entity extraction. Also a stub (intentionally unimplemented, raises with a clear message) for the OpenNyAI rhetorical-role model — see §6. |
| `poc_run.py` | 315 | CLI proof runner. Loads the ML model eagerly (mandatory), runs all pipeline stages on a folder of PDFs, writes `poc_report.md` (human-readable proof, includes a "Parties" section showing which tier/confidence each document resolved at) and `poc_graph.json` (React-Flow-ready). |

### Test files (all pass with **no PDF and no model download** — pure logic, run in under a second, except `dryrun_real.py`/`test_opennyai_bridge.py` which need spaCy installed)

| File | Groups | Proves |
|---|---|---|
| `test_logic.py` | 7 | Core pipeline: offset→page mapping, None-safety, type-aware normalization, blocking efficiency, bi-temporal invalidation, polarity/edge labelling, structure fallback |
| `test_layout.py` | 6 | Layout-signal structure detection: scoring, OCR-mangled headings, OCR word-box→line grouping, noise filter (running headers vs real headings), contents-page ratio detection, section partitioning |
| `test_profile_symbols.py` | 6 synthetic cases | Party extraction across document types: plaint, affidavit, OCR-mangled, Hindi, legal notice, contract |
| `dryrun_real.py` | 8 real documents | Party extraction against real Supreme Court/High Court/NCLT judgments — see §5 |
| `test_opennyai_bridge.py` | 20 checks, 6 groups | The mandatory ML layer's glue code, tested against spaCy's **real** Doc/Span API with a faked entity source (see §2 constraint 5) |
| `dryrun_fallbacks.py` | — | Forces every tier of all three ladders deliberately (missing deps, OCR damage, empty files, garbage input) |

**Current status: all pass.** Run them in this order if you change anything: `test_logic.py` → `test_layout.py` → `test_profile_symbols.py` → `dryrun_real.py` → `test_opennyai_bridge.py`.

### Real document corpus (regression oracle — do not delete)

- `real_docs/` — 8 `.txt` files, verbatim text from real, publicly available 2024–2025 Indian judgments (Supreme Court, Delhi High Court, NCLT), fetched from `api.sci.gov.in` and similar. Covers: multi-appeal SC judgments, insolvency/NCLT tribunal roles, matrimonial/maintenance, tax, land acquisition, Delhi HC bail with advocate blocks, criminal appeal.
- `real_pdfs/` — 6 `.pdf` files, the same real judgment text **rendered** into PDFs with varying container properties (bookmarked, headings-only, flat/no-structure, separator pages, and **2 genuinely rasterised with no text layer at all**, forcing real OCR). Built by `make_real_pdfs.py`. These are what surfaced BUG-26 (see §4).

### Documentation (chronological — later files supersede earlier claims where they conflict)

`CaseMap_Technical_Build_Spec.md` → `CaseMap_Code_Review_and_Fixes.md` → `CaseMap_Layout_Structure_v3.md` → `CaseMap_Profiles_Symbols_TechStack_v4.md` → `CaseMap_Real_Document_DryRun_v5.md` → `CaseMap_Fallbacks_TechStack_v6.md` → `FALLBACK_DRYRUN_RESULTS.md` → `CaseMap_Mandatory_ML_Layer_v7.md` (most current on the ML layer) → **this file** (most current overall).

`blueprint1.md` / `blueprint2.md` — the original product scope and hard-boundary documents (what NOT to build in 72 hours). Still valid; nothing here has violated those boundaries.

---

## 4. Complete bug ledger (26 bugs, all fixed and verified — read before "fixing" something that looks broken, it may already have a documented reason)

Grouped by what found them:

**Found by code review / self-testing (BUG-1 to BUG-12):**
1. `.get(k, {}).get(v)` crashed on explicit `None` values (not absent keys) — `to_react_flow`/`build_evidence_card`
2. **Provenance pointed at the first page of a multi-page section**, not the actual page a fact was on — silent, critical, fixed with char-offset→page mapping
3. `fitz.open()` reopened per page during OCR — O(pages) file opens
4. `doc.get_toc()` called per page instead of once
5. Entity normalization matched across types (a PERSON could merge into an ORG)
6. `score_pair()` read `section_text`, never set by `detect_events()`
7. Dead code / unused variable in normalization
8. No OCR caching → minutes per POC re-run
9. POC's similarity function was a constant `0.5` stub — every score identical, "proving" nothing
10. spaCy's ~1M char limit unhandled on long documents
11. TOC detection only matched dot-leader lines, not whitespace-column layout (common in Indian indexes)
12. Fuzzy name key kept single-char abbreviations, so `ABC P. Ltd.` ≠ `ABC Pvt Ltd`

**Found by structure-detection dry run (folded into the layout ladder):** fuzzy matching used the wrong unit (sliding `partial_ratio` over a whole line misses OCR corruption *inside* a word — fixed with token-level comparison); noise filter's "protect bold/centered lines" rule shielded running headers, which are themselves often centered — fixed by letting cross-page repetition override emphasis.

**Found by real-document dry run, round 1 (BUG-13 to BUG-17 in party-extraction numbering):**
13. Multi-appeal judgments (`WITH` joining several cause titles) — only the first `VERSUS` was found; block walk ran past the second cause title into judgment body
14. Letter-spaced headings (`J U D G M E N T`) matched no boundary pattern
15. Judge signature lines (`VIKRAM NATH, J.`) extracted as parties
16. Case headings with ranges/blanks (`NOS. 5023-5024`, `NO. OF 2024`) matched nothing, degrading role confidence
17. Numbered PARTY entries vs numbered BODY paragraphs both look like `"1. Something"` — a regression introduced fixing #13 silently dropped every defendant in a numbered list; fixed by checking for role markers / finite verbs / sentence-length

**Found by real-document dry run, round 2, harder courts (BUG-18 to BUG-23):**
18. **Advocate blocks inside the party block** — High Court cause lists put `Through: Mr. X, Advocate...` between the party name and the separator; every counsel became a "party." (This is the standard High Court layout, not an edge case.)
19. Delhi HC listing markers (`$~`, `*`, `%`, `+`) at line start
20. Tribunal role vocabulary missing (`Financial Creditor`/`Corporate Debtor` for NCLT)
21. Case number matched from deep in the body (4000-char window too wide) instead of the heading
22. Registry short-form case numbers with no "No." (`BAIL APPLN. 4102/2024`)
23. Statutory-reference recital blocks (`In the matter of\nSection 7 of...`) treated as parties

**Found by fallback-ladder adversarial testing (BUG-24, the worst one):**
24. **OCR-damaged text produced garbage parties at HIGH confidence** (`REP0RTA8LE`, `1N THE 5UPREME C0URT`). First fix used a blanket character-substitution probe that corrupted genuine numbers (`2024`→`2O24`), letting a damaged case heading still slip through. Final fix: `_ocr_probe()` normalizes only alphabetic tokens; `_ocr_mangled_ratio()` rejects at ≥34% of tokens carrying an in-word digit. Now returns `tier5_none` instead of confident garbage. **This was flagged as the single worst failure mode possible for this product** — not a crash, but confidently wrong data.

**Found building the mandatory ML layer (BUG-25, BUG-26):**
25. Repeated model-load attempts (and repeated warning banners) once per document instead of once per run — fixed with an `_UNSET` sentinel distinguishing "caller omitted `nlp`" from "caller explicitly resolved it to `None`"
26. **OCR text reconstruction discarded ALL line breaks** — `_ocr_tesseract()`/`_ocr_paddle()` joined every word with a single space regardless of position, fusing an entire cause title into one line so `VERSUS` never stood alone and every line-based rule silently failed. This is a pre-existing bug (not caused by the ML work) that was invisible until the mandatory-layer testing forced a genuine end-to-end run against **rendered PDFs** rather than plain `.txt` files — every prior dry run had used `.txt`, never actually exercising OCR. Fixed by reusing `layout_structure.py`'s existing row-grouping logic. Verified: one real scanned document went from `tier5_none` to `tier1_cause_title/high` after the fix.

**Residual, logged not hidden:** after BUG-26's fix, one party's role still resolves via `case_type` inference rather than `explicit`, because OCR rendered "Respondents" as "Raspondents" (a/e swap) and the role-marker regex expects exact spelling. Correct party, slightly less precise role-confidence tag. Not yet fixed — see §7.

---

## 5. Real-document dry run results (current state)

**8 real documents** (`real_docs/*.txt`) — Supreme Court (5, including one multi-appeal judgment), Delhi High Court bail, NCLT insolvency, Supreme Court criminal appeal:

```
17 party symbols, 0 garbage, 17/17 explicit roles, review queue empty
```

**6 real PDFs** (`real_pdfs/*.pdf`), run through the full mandatory pipeline in `--allow-degraded` mode (ML model not installed in this sandbox — see constraint 5):

```
6/6 documents resolve at tier1_cause_title, confidence high
(2 of these are genuinely rasterised with zero text layer, recovered via real OCR)
```

Both numbers reflect the state **after** all 26 bugs above were fixed. If you re-run and get worse numbers, something regressed — check the bug ledger before assuming it's a new document-format problem.

---

## 6. Two ML models identified, one integrated

**Integrated (mandatory, per explicit instruction):** OpenNyAI's `en_legal_ner_sm`/`en_legal_ner_trf` (spaCy pipelines, Apache 2.0, Kalamkar et al. NLLP 2022, F1 91.08 reported for `trf`). Outputs `PETITIONER`/`RESPONDENT`/`COURT`/`JUDGE`/`STATUTE`/`PROVISION`/`DATE`/etc. as literal labels — this is the model that generalises across courts the regex ladder was never tuned for. Wired in `opennyai_bridge.py` + `document_profile.extract_parties_hybrid()`. **Never loaded with real weights in this sandbox** (huggingface.co blocked) — only glue-tested.

**Identified, NOT integrated (stub only, raises intentionally):** OpenNyAI's rhetorical-role classifier (Kalamkar et al., LREC 2022, "Corpus for Automatic Structuring of Legal Documents" — the `BUILD` corpus, dataset on HF as `opennyaiorg/InRhetoricalRoles`, CC BY-SA 4.0). This would label judgment *sentences* as Facts/Arguments/Ratio/Ruling — a different, complementary job to `layout_structure.py` (which finds *visual* section boundaries; this would find *semantic* content type where there's no visible heading at all, which is most of a judgment's body). **No confirmed simple load API was found** for this one (unlike the NER model, which had documented `spacy.load(...)` usage) — it lives in a GitHub repo with its own inference script. `load_rhetorical_role_model()` in `opennyai_bridge.py` is a clean seam that always raises with this explanation. Do not claim this is working until you've confirmed the actual inference entrypoint.

**Investigated and explicitly rejected, with reasons (do not re-propose without new evidence):**
- **AYN** (arXiv 2403.13681, 88M params, Indian legal, LREC 2026) — real model, but decoder-only *generative*, built for judgment prediction/summarization. Wrong tool shape for extraction; using it would reopen the hallucination risk this whole build avoids. No confirmed public checkpoint found either.
- **"dinghy-law-0.6b-v1"** — a garbled conflation from an external source. The real 0.6B CPU-quantizable model is **GreenLeaf Law Embed Tiny** (arXiv 2608.24936); "Dinghy Law" is a separate, unrelated **8B** model. If you see this name again, it's wrong — correct to GreenLeaf if a small embedding model is what's actually needed (it isn't currently — MiniLM/BGE-M3 already cover that role).
- **InLegalBERT** — real (~110M, BERT-base, Indian legal corpus), but a base encoder requiring your own fine-tuning for any specific task (segmentation, classification). Not a drop-in.

---

## 7. Open gaps (ordered by value, not difficulty)

1. **Install the real OpenNyAI model and actually run it.** This is the single highest-priority item and the one thing this sandbox structurally cannot do. Run `poc_run.py` (folder of real PDFs) **without** `--allow-degraded` and confirm: (a) it loads, (b) label casing matches `PARTY_LABELS_TO_SIDE` in `opennyai_bridge.py` (currently transcribed from docs, unverified against live weights), (c) accuracy on `real_docs/`/`real_pdfs/` is actually better than the regex-only ladder, not just differently wrong.
2. **Act-name inheritance for bare section citations.** Confirmed across all 8 real documents: `Section 24 of the Hindu Marriage Act, 1955` and a later bare `Section 24` are currently two separate symbols. Fix: carry the last-seen Act forward within a document in `case_symbols.py`.
3. **OCR-tolerant role-marker matching.** The `Raspondents` residual from BUG-26 — extend the existing OCR-probe pattern (already used for party-name rejection in `document_profile.py`) to `ROLE_MARKER_RE` matching too.
4. **Amount figures-vs-words cross-check.** Both `₹1,20,00,000` and `Rupees One Crore Twenty Lakh` are extracted (see `case_symbols.normalize_amount`/`amount_from_words`) but never compared against each other. A mismatch is either an OCR error or a real drafting error — both worth surfacing, cheap to add.
5. **`& Ors.` / `& Anr.` expansion.** Currently collapses multiple respondents into one symbol.
6. **Same party, different roles across documents.** `Party.role` / symbol `attributes["role"]` is single-valued; a party can be Petitioner in one filing and Respondent in a connected appeal.
7. **Confirm the rhetorical-role model's real API** before building anything on top of the current stub (§6).
8. **React Flow UI** — not started. `poc_run.py` already writes `poc_graph.json` in the right shape; this is normal frontend work once the above is stable, not a research problem.
9. **PDF.js click-to-source viewer** — not started, same status as above.

---

## 8. How to run everything right now

```bash
# Pure logic tests — no downloads, run in under a second each
python3 test_logic.py
python3 test_layout.py
python3 test_profile_symbols.py

# Needs spaCy + its base English model (already installed in this session
# via: pip install spacy --break-system-packages
#      pip install <github release wheel for en_core_web_sm> )
python3 dryrun_real.py
python3 test_opennyai_bridge.py

# Full pipeline against real rendered PDFs — mandatory model not installed
# here, so --allow-degraded is required in THIS sandbox. Remove that flag
# once the real OpenNyAI weights are installed.
python3 poc_run.py real_pdfs --ocr tesseract --allow-degraded

# To install the real mandatory model (blocked in this sandbox, should work
# in an environment with normal internet access):
pip install https://huggingface.co/opennyaiorg/en_legal_ner_sm/resolve/main/en_legal_ner_sm-any-py3-none-any.whl
python3 poc_run.py real_pdfs --ocr tesseract      # no --allow-degraded
```

Dependencies already confirmed working in this sandbox: `pymupdf`, `rapidfuzz`, `opencv-python-headless`, `pillow`, `spacy` (+ `en_core_web_sm` via GitHub release wheel), `dateparser`, `pytesseract` + system `tesseract-ocr` binary. **Not installed/confirmed here:** `paddleocr`/`paddlepaddle`, `sentence-transformers` (code has graceful degradation if absent — see `casemap_pipeline.make_similarity_fn()`), the actual OpenNyAI model weights.

---

## 9. Tech stack summary (see `CaseMap_Fallbacks_TechStack_v6.md` for full detail)

**Backend:** Python 3.11+, FastAPI (not yet wired — currently CLI-only via `poc_run.py`), PyMuPDF, PaddleOCR (default)/Surya/Tesseract (fallback), OpenCV, spaCy (+ OpenNyAI legal model, mandatory), rapidfuzz, dateparser, sentence-transformers (MiniLM default, BGE-M3 upgrade path), SQLite (symbols + bi-temporal edges — no Neo4j).

**Frontend (not yet built):** Next.js, React Flow, PDF.js, Tailwind + shadcn/ui.

**Deliberately rejected, with reasons already litigated — do not re-propose without new evidence:** Neo4j/Graphiti (extra service, can fail on demo day; SQLite `TemporalEdge` gives the same bi-temporal invalidation in ~40 lines), ColPali/ColQwen (needs a GPU), any generative LLM in the core extraction/graph loop (breaks the traceability claim), Qdrant/Weaviate/Elasticsearch (unnecessary at this scale), Docker for the hackathon demo (setup risk on the day).

---

## 10. If you are a coding agent picking this up cold

Read in this order: this file → `blueprint1.md`/`blueprint2.md` (original scope) → `CaseMap_Mandatory_ML_Layer_v7.md` (most recent deep-dive) → skim the bug ledger in §4 above so you don't "fix" something that's actually a documented, tested design choice. Then run the test suite in §8 to confirm you're starting from a green baseline before changing anything. The single most valuable next action is §7 item 1 — install the real model and report back whether its accuracy justifies its mandatory status, since that has never actually been verified end-to-end.
