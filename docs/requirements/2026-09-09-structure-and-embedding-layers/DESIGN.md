# Design: Docling-backed structure detection + Qwen3-Embedding similarity

**Date:** 2026-09-09
**Requirements:** `REQUIREMENTS.md` in this folder.

## The existing seam, read directly from `src/casemap_pipeline.py`

```python
def segment_document_layered(pdf_path: str, pages: list[dict],
                             toc: list | None = None) -> tuple[list[dict], dict]:
    try:
        from layout_structure import detect_structure_layered
    except ImportError:
        signals = detect_structure(pages, toc or [])
        return segment_document(pages, signals), {
            "tier": "legacy_text_patterns", "confidence": "unknown",
            "tier_reason": "layout_structure module not importable",
            "stats": signals}

    result = detect_structure_layered(pdf_path, pages, toc)
    return result.sections, {"tier": result.tier, "confidence": result.confidence,
                             "tier_reason": result.tier_reason, "stats": result.stats}
```

This already does everything FR3 needs at the *call site* level — if
`layout_structure` can't even be imported, it falls back cleanly. What's missing is
`layout_structure.py` itself. This design fills that gap with a Docling-backed
implementation, not a hand-rolled heuristic ladder — because
`layer-additions-assessment.md` already validated Docling does this job correctly, on
both digital and genuinely-scanned PDFs.

## `LayeredStructureResult` — inferred from the call site, not invented

The call site does `result.sections`, `result.tier`, `result.confidence`,
`result.tier_reason`, `result.stats`. So:

```python
@dataclass
class LayeredStructureResult:
    sections: list[dict]   # same shape segment_document() already returns
    tier: str              # e.g. "docling_layout", "legacy_fallback_internal"
    confidence: str        # "high" | "medium" | "low" — surfaced per NFR2
    tier_reason: str
    stats: dict
```

## `detect_structure_layered()` — the actual new function

```python
def detect_structure_layered(pdf_path: str, pages: list[dict],
                              toc: list | None = None) -> LayeredStructureResult:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        # Docling itself unavailable — degrade internally, per FR3.
        # Reuses casemap_pipeline's own legacy detector via a late import to
        # avoid a circular import (layout_structure <-> casemap_pipeline).
        from casemap_pipeline import detect_structure, segment_document
        signals = detect_structure(pages, toc or [])
        return LayeredStructureResult(
            segment_document(pages, signals), "legacy_fallback_internal",
            "unknown", "docling not installed", signals)

    try:
        result = DocumentConverter().convert(pdf_path)
        headings = [
            {"page": item.prov[0].page_no, "text": item.text}
            for item, _level in result.document.iterate_items()
            if str(getattr(item, "label", "")) == "section_header"
            and getattr(item, "prov", None)
        ]
    except Exception as e:  # Docling raised — degrade, don't propagate (FR3)
        from casemap_pipeline import detect_structure, segment_document
        signals = detect_structure(pages, toc or [])
        return LayeredStructureResult(
            segment_document(pages, signals), "legacy_fallback_docling_error",
            "unknown", f"docling raised: {e}", signals)

    if not headings:
        from casemap_pipeline import detect_structure, segment_document
        signals = detect_structure(pages, toc or [])
        return LayeredStructureResult(
            segment_document(pages, signals), "legacy_fallback_no_headings",
            "unknown", "docling found no section_header items", signals)

    from casemap_pipeline import _segment_by_headings
    sections = _segment_by_headings(pages, headings)
    return LayeredStructureResult(sections, "docling_layout", "high",
                                   f"docling found {len(headings)} headings",
                                   {"heading_count": len(headings)})
```

**Every exit path is a real, already-existing shape** — `_segment_by_headings` and
`segment_document`/`detect_structure` are not reimplemented, only called. This is the
same "no parallel implementation" discipline both prior POCs (fallback-nodes,
layer-additions) already followed.

**Open question for implementation, not resolved here:** does `item.prov[0].page_no`
reliably give a 1-indexed or 0-indexed page number matching `pages[i]["page_number"]`'s
convention? The POC scripts (`run_docling.py`) never checked this — they only counted
items, never cross-referenced page numbers against `casemap_pipeline`'s own page
records. **This must be verified with a real multi-page document before FR2 is
considered met**, not assumed from the single-field name match.

## Qwen3-Embedding: two possible integration paths, only one tested

`layer-additions-assessment.md`'s POC used Ollama's local HTTP API
(`qwen3-embedding:0.6b`) — convenient for a fast script, but **not** the code path
`make_similarity_fn()` actually uses in `src/`:

```python
def make_similarity_fn(model_name: str = "all-MiniLM-L6-v2"):
    def fn(e1, e2):
        ...
        from sentence_transformers import SentenceTransformer
        if _EMBED is None:
            _EMBED = SentenceTransformer(model_name)
        ...
```

The **cleanest** integration (zero new code, one changed default) would be
`make_similarity_fn(model_name="Qwen/Qwen3-Embedding-0.6B")` — **if** that Hugging
Face checkpoint loads correctly via plain `SentenceTransformer(...)`. Qwen3-Embedding
was released with sentence-transformers support, so this is plausible, but **it was
never actually tried** — the POC only exercised the Ollama path. This is the single
most important open item before `TASKS.md` claims Qwen3-Embedding is "done": confirm
`SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")` actually works standalone, in the
project's real dependency set, before deciding whether an Ollama-backed second path is
needed at all.

## Confidence/tier surfacing (NFR2)

`segment_document_layered()`'s return already threads `tier`/`confidence` through to
its caller as `meta`. Real implementation must confirm whatever consumes that `meta`
downstream (report generation, `poc_run.py` output) actually renders it, not just
that it's present in the dict — same principle as the fallback-nodes requirement's T4.

## What's explicitly deferred

- MinerU comparison (`REQUIREMENTS.md` non-goals).
- Wiring `layout_structure.py`'s output through to the React Flow / evidence-card
  layer (stage [6] isn't built yet, per `HEART.md`).
- Docling's own OCR path (RapidOCR/PP-OCR) replacing or coexisting with
  `casemap_pipeline`'s existing 3-tier OCR ladder (PaddleOCR/Surya/Tesseract) — this
  design only uses Docling for structure detection given already-extracted `pages`
  text; it does not evaluate Docling as a full OCR replacement. Worth a separate,
  explicit requirement if pursued — the two OCR stacks producing different text for
  the same document is a real coordination risk not analyzed here.
