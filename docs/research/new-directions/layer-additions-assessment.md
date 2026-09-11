# Assessment: Docling (structure) + Qwen3-Embedding (similarity) added as layers, tested together

**Date:** 2026-09-09
**Status:** POC only, not adopted, not wired into `src/`.
**Why this exists:** following the mini-LLM (`mini-llm-extraction-assessment.md`) and
`en_legal_ner_sm` assessments, the owner asked about six other tools (Docling, MinerU,
GLiNER2, NuExtract 2.0, Qwen3-Embedding, HippoRAG 2) and specifically asked to test
**Docling/MinerU + Qwen3-Embedding together**, not in isolation, to see whether they
actually compose — not just whether each works alone.

## Why these two, and not the other four

Per the same-day discussion (not repeated in full here): **NuExtract 2.0** is
architecturally generative (autoregressive decoding fine-tuned for extraction) —
same category `FORBIDDEN.md` §C already excludes from the core, and F-1's Qwen2.5
test already demonstrated the concrete risk that rule exists for. **HippoRAG 2**
needs real graph infrastructure, the same complexity `CaseMap_AGENT_HANDOFF.md` §9
already rejected Graphiti/Neo4j for. **GLiNER2** and **MinerU** are reasonable
follow-ups, not tested this round — see "Not yet tested" below.

**Docling** was picked over MinerU as the first structure-detection candidate because
it addresses a real gap: `layout_structure.py` — the module that would normally do
5-tier structure detection — **does not exist in this working directory** (see
`HANDOFF.md` §6). This isn't a replacement decision, it's recovering missing
capability. **Qwen3-Embedding** (`qwen3-embedding:0.6b` via Ollama, 639MB, smaller
than the `qwen2.5:1.5b` tested in F-1) slots into the exact place
`casemap_pipeline.make_similarity_fn()` already reserves for MiniLM/BGE-M3 — a
drop-in swap, not a new architectural role.

## Setup honesty: PDFs had to be manufactured

`testdata/` is plain text, not PDFs — it can't test a PDF layout parser at all. Real
PDF judgments were not obtainable cleanly (indiankanoon's PDF export is JS-driven, not
a stable link; scraping it wasn't attempted). Instead, 4 `testdata/*.txt` files were
rendered to real PDFs with a genuine font-size/bold hierarchy (title, forum line,
"JUDGMENT"/"ORDER" markers all distinct from body text) via
`temp/2026-09-09-layer-additions-poc/make_test_pdfs.py` — the same principle the
pre-governance project used for its own real-PDF dry run
(`CaseMap_AGENT_HANDOFF.md` §5, "6 real PDFs"). **Stated limitation, not hidden: this
tests digital-PDF layout parsing only, not scanned/OCR-damaged input** — the failure
mode `FORBIDDEN.md` §E18/BUG-26 actually cares about. A second pass against genuinely
scanned PDFs is still needed before Docling's OCR-input behavior is validated.

## Part 1 — Docling alone

Ran `docling` (2.126.0, ~1.5GB install with its own layout + OCR models, CPU) against
4 rendered PDFs (the connected Cygnus Splendid Ltd bundle: docs 09/21/22, plus an
unrelated document, 01, as a distractor). Script:
`temp/2026-09-09-layer-additions-poc/run_docling.py`, raw output:
`docling_results.json`.

**Cost:** first document took 90.8s (one-time model download + load from Hugging
Face/ModelScope — needs internet on first run); every document after that took
1.6-8.3s.

**Quality — genuinely correct, not just plausible-looking:** Docling's layout model
(not a heuristic like the font-size-relative-to-median approach `layout_structure.py`
was designed around) correctly labelled the title, the forum line
("NATIONAL COMPANY LAW APPELLATE TRIBUNAL..."), "Present:", and "JUDGMENT"/"ORDER" as
`section_header`, and distinguished `list_item` from plain `text` for numbered
paragraphs — using the actual font hierarchy in the PDF, not keyword matching. This is
at least as good as what a hand-rolled heuristic ladder would produce, for less code.

## Part 2 — Qwen3-Embedding alone (as a `similarity_fn` swap)

`casemap_pipeline.score_pair()`'s `semantic_score` term already expects a
`similarity_fn(e1, e2) -> float`. Wrote one backed by `qwen3-embedding:0.6b`'s local
Ollama API instead of MiniLM/BGE-M3 — no change to `score_pair` itself, just a
different function passed in, exactly the seam `make_similarity_fn()` already
provides.

## Part 3 — Both together, through the real graph pipeline

`temp/2026-09-09-layer-additions-poc/poc_combined_layers.py`: Docling's recovered
text feeds `en_legal_ner_sm` (already-validated entities, F-2) for
`linked_entities`, Qwen3-Embedding supplies `semantic_score`, and the resulting
events run through `casemap_pipeline.build_inverted_index` /
`generate_candidate_pairs` / `score_pair` / `sparsify_and_cluster` / `to_react_flow`
**unmodified** — same discipline as the fallback-nodes POC: no parallel
reimplementation of pipeline logic.

**Result — clean and correct:**

| Pair | Score | Edge? |
|---|---|---|
| 09 (NCLAT 2023) ↔ 21 (NCLAT 2025, same matter) | 0.393 | **Yes** |
| 09 ↔ 22 (SC 2025, appeal of 21) | 0.296 | **Yes** |
| 21 ↔ 22 (direct appeal relationship) | 0.615 | **Yes** — strongest, as expected |
| 01 (unrelated criminal case) ↔ any of 09/21/22 | 0.122 – 0.139 | No |

All three genuinely-connected documents linked to each other; the unrelated document
never crossed the edge threshold, **even though its raw semantic similarity score
(0.35-0.40) was not negligible** — any two Indian court judgments read alike at the
embedding level. What kept it from producing a false edge was `score_pair`'s existing
weighting (35% entity overlap, 35% semantic, 20% temporal, 10% same-doc) — semantic
similarity alone was never enough; it needed the entity signal too, which the
unrelated document correctly lacked. This is the graph's existing design working as
intended, not a property of the new layers — worth noting as reassurance that adding
a strong embedding model doesn't on its own risk over-connecting unrelated documents.

One incidental finding: this run's entity overlap for 21↔22 came back `1.0` — a full
match — **without** calling `normalize_entities()` (unlike the fallback-nodes POC,
which needed it to catch an ALL-CAPS mismatch). The difference: this script pulled
entities from the full per-document NER run (`results_en_legal_ner_sm.json`), which
had multiple mentions of "Sunil Kumar Gupta" in mixed case across the whole document,
so at least one shared exact-string mention existed — whereas the fallback-nodes POC
only looked at a short truncated span. **This does not remove the need for
`normalize_entities()`** (`DESIGN.md`'s T3) — it shows the gap is real but narrower
when full-document context is available; a fallback node built from a short span (the
whole point of the fallback-nodes feature) is exactly the case with the least context
to fall back on, so normalization stays necessary there.

## Part 4 — Docling against genuinely scanned/OCR-damaged PDFs (the gap this file originally flagged as open)

The owner asked to close this gap rather than leave it as a stated limitation.
`temp/2026-09-09-layer-additions-poc/make_scanned_pdfs.py` takes 2 of the digital
PDFs from Part 1 (docs 09, 21) and produces genuinely scanned-style versions: each
page rendered to a raster image via PyMuPDF, then degraded with real artifacts —
±1.2° rotation (scanner skew), Gaussian blur (focus softness), and salt-and-pepper
noise (0.4% of pixels) — and rebuilt into a PDF containing **only the images, zero
embedded text layer** (verified with `page.get_text()` returning 0 characters before
the OCR run). This is not cosmetic degradation; it forces Docling's actual OCR engine
(RapidOCR) to run, the same way a real scanned court filing would.

**Result: structure detection survived.** All headings that Part 1's clean-PDF run
found — the case title, the forum line, `"IN THE MATTER OF:"`, `"Present:"`,
`"ORDER"` — were correctly labelled `section_header` again, and numbered paragraphs
were again correctly split into `list_item`s (doc 21). Party names and the core facts
(`"Vijay Kumar Singhania"`, `"Bank of Baroda"`, `"Sunil Kumar Gupta"`,
`"Cygnus Splendid Limited"`) all survived legibly.

**Real, honest costs of the OCR path, not hidden:**
- **Slower:** 18.05s and 12.96s per document (vs. 1.6-8.3s on the clean-PDF path) —
  real OCR is not free.
- **More fragmented, and character-level damage appeared:** item counts were higher
  (34 vs. 13 for doc 09) — OCR gives per-line boxes rather than the PDF's own
  paragraph grouping, so text that was one clean paragraph in Part 1 came back as
  several shorter items here. Dropped spaces at word boundaries showed up repeatedly
  (`"Anron13 December"`, `"NATIONALCOMPANY LAWAPPELLATE"`, `"NewDelhi-110008"`,
  `"2.Sunil Kumar Gupta"`) — the same general class of OCR word-boundary damage
  `FORBIDDEN.md` §E18/BUG-26 already documents for this project's own OCR path, now
  independently observed in Docling's OCR path too. It didn't corrupt the
  identifying content in this test, but it is exactly the kind of damage a
  downstream regex/NER step needs to be tolerant of (the project's existing
  `is_versus_line()` fuzzy-match pattern already exists for precisely this reason).

## Conclusion

The three additions compose correctly on this small test: Docling recovers real
structure without `layout_structure.py` existing, Qwen3-Embedding drops into the
existing similarity-function seam with zero pipeline changes, and together with the
already-validated `en_legal_ner_sm` they produce a correctly-discriminating graph
through the unmodified `casemap_pipeline` functions — connected documents connect,
unrelated ones don't, on real (if digitally-rendered) legal text.

**Before this is more than a POC:**
- Docling's 1.5GB footprint and 90s cold start (or up to 18s/doc under real OCR) are
  real integration costs — worth a head-to-head against MinerU before picking one
  (checked MinerU's own dependency footprint: not actually lighter — its `pipeline`
  and `vlm` extras both require `torch`/`transformers`, and `vlm` needs a full
  vision-language model, likely heavier than Docling, not tested end-to-end here).
- Only 4-6 documents were tested across all parts. The clean discriminating result is
  encouraging, not proof at scale.
- Real OCR introduces real, if modest, text damage (word-boundary space loss) — any
  downstream party/entity matching consuming Docling's OCR output needs the same
  OCR-tolerant matching discipline the project's regex ladder already has
  (`is_versus_line()`), not exact-string assumptions.
- `normalize_entities()` remains a required step for real implementation
  (`docs/requirements/2026-09-09-verbatim-fallback-nodes/DESIGN.md` T3), not made
  optional by this run's incidental success.

## Not yet tested

- **MinerU** — dependency footprint checked (not lighter than Docling — see above),
  but no actual conversion run/head-to-head done.
- **GLiNER2** — flagged as a legitimate supplementary NER experiment, not run.
- This is still 2 documents rendered-then-degraded, not genuinely scanned originals
  or the project's own `real_pdfs/` corpus (still absent, `HANDOFF.md` §6) — a real
  scanned document (uneven lighting, staple marks, genuine low-DPI artifacts) is a
  further, harder test this didn't reach.

## Where things are, for the next session

`temp/2026-09-09-layer-additions-poc/` — `make_test_pdfs.py`, `run_docling.py`,
`poc_combined_layers.py`, the 4 generated PDFs, and both raw JSON results. The Docling
venv (`venv_docling/`, ~1.5GB) is left in place — expensive to rebuild (models
downloaded from HF/ModelScope) — but is ephemeral per `AGENTS.md` §9 and safe to
delete once this write-up is trusted.
