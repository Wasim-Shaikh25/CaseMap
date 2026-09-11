# Requirements: Docling-backed structure detection + Qwen3-Embedding similarity

**Date:** 2026-09-09
**Read first:** `FORBIDDEN.md`, `AGENTS.md`, `THESIS.md`, `docs/spec/SCOPE.md`,
`docs/spec/ARCHITECTURE.md`. Research backing this requirement:
`docs/research/new-directions/layer-additions-assessment.md` (all 4 parts — Docling
alone, Qwen3-Embedding alone, both together, both against genuinely scanned/OCR-only
PDFs) and `FINDINGS.md` F-4.

## Problem

`docs/spec/ARCHITECTURE.md` §2 lists `layout_structure.py` (structure detection, the
5-tier ladder) as a component of this pipeline. It **does not exist in this working
directory** (`HANDOFF.md` §6). `casemap_pipeline.segment_document_layered()` already
has a working, graceful fallback for its absence — see `DESIGN.md` for the exact
mechanism — but that fallback (`detect_structure`/`segment_document`, a TOC-pattern +
bookmark + `ANNEXURE_PATTERN`-heading scorer) is markedly weaker than what a real
layout-aware detector would recover, especially on documents with no index page and no
PDF bookmarks.

Separately, `casemap_pipeline.make_similarity_fn()` defaults to `all-MiniLM-L6-v2`
and documents `BAAI/bge-m3` as "the upgrade path" in its own docstring — that upgrade
has never actually been evaluated against an alternative.

## Goal

1. Recover real structure-detection capability by implementing
   `layout_structure.detect_structure_layered()` — the exact interface
   `casemap_pipeline.py` already expects and gracefully degrades without — backed by
   Docling, which `docs/research/new-directions/layer-additions-assessment.md`
   validated (headings/list-items correctly recovered, on both digital and genuinely
   OCR'd/degraded PDFs).
2. Evaluate whether `Qwen3-Embedding-0.6B` is a real, working drop-in for
   `make_similarity_fn()`'s existing `model_name` parameter, or whether it needs a
   second code path (the POC used Ollama's local API for convenience, not the
   `sentence_transformers` path `make_similarity_fn()` actually uses — see
   `DESIGN.md`'s open question on this).

## Non-goals

- **Not replacing the deterministic OCR/party/date/amount extraction ladders.** This
  requirement only touches structure detection (stage [1]) and semantic similarity
  (part of stage [5]'s `score_pair`). No change to `document_profile.py`'s party
  extraction or `casemap_pipeline.extract_deterministic()`.
- **Not a MinerU integration.** `layer-additions-assessment.md` checked MinerU's
  dependency footprint (not lighter than Docling) but never ran it — no MinerU code
  path is in scope here. A future comparison is a separate requirement if pursued.
- **Not required to beat the legacy TOC/bookmark detector in every case.** The legacy
  path is a real, working fallback (`ANNEXURE_PATTERN`, TOC-dotted/columnar regex,
  bookmark scoring) — this requirement adds a *better* tier ahead of it via the
  existing `try/except ImportError` seam, it does not remove or need to out-perform
  the fallback in every scenario (the fallback stays as tier N when Docling itself
  fails to import/run — same "never hard-depend on it" principle already documented
  in `segment_document_layered()`'s own docstring).

## Functional requirements

1. **FR1 — `layout_structure.py` implements `detect_structure_layered(pdf_path, pages, toc) -> LayeredStructureResult`**,
   the exact signature `casemap_pipeline.segment_document_layered()` already calls.
   `LayeredStructureResult` needs `.sections` (same shape `segment_document()`
   produces: `[{"section_label": str, "pages": [...], "detected": bool}]`),
   `.tier`, `.confidence`, `.tier_reason`, `.stats` — inferred directly from the
   existing call site, not invented (see `DESIGN.md`).
2. **FR2 — Docling runs on `pdf_path`, and its recovered heading items (with page
   numbers) are converted into the same `headings: [{"page": int, "text": str}]`
   shape `casemap_pipeline._segment_by_headings()` already consumes** — reusing that
   existing function rather than reimplementing page-grouping logic.
3. **FR3 — Never hard-depend on Docling.** If Docling is not installed, or raises,
   `detect_structure_layered()` must not crash the pipeline — the existing
   `try/except ImportError` in `segment_document_layered()` already handles the case
   where `layout_structure` itself can't be imported; `detect_structure_layered()`
   internally must similarly degrade (e.g. to the legacy `detect_structure()` logic,
   or an even simpler single-page-per-section split) rather than propagate an
   exception, consistent with `docs/spec/ARCHITECTURE.md` §3's standing rule ("every
   stage's fallback ladder always terminates").
4. **FR4 — Evaluate `Qwen3-Embedding-0.6B` against `make_similarity_fn()`'s actual
   `sentence_transformers` code path**, not just the Ollama API path the POC used —
   determine whether `SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")` loads and
   produces usable embeddings with zero code change beyond the `model_name` argument,
   or whether Qwen3-Embedding needs different handling (see `DESIGN.md` open
   question).

## Non-functional requirements

- **NFR1 — No regression to the legacy structure-detection fallback's existing
  behavior** when Docling is unavailable — `segment_document()`/`detect_structure()`
  remain untouched.
- **NFR2 — Confidence must be surfaced, not hidden**, per `FORBIDDEN.md` §E15/G1 —
  `LayeredStructureResult.confidence`/`.tier` must distinguish a Docling-derived
  result from a legacy-fallback one downstream.
- **NFR3 — Terminates, never crashes** (`docs/spec/ARCHITECTURE.md` §3).

## Acceptance / validation

Per this project's established discipline (`FORBIDDEN.md` §E17): validate against real
documents, not synthetic ones alone. `layer-additions-assessment.md` already validated
Docling's structure recovery on both digital and genuinely-OCR'd PDFs (Parts 1 and 4)
— real implementation (`TASKS.md`) must re-validate through the actual
`layout_structure.py` module and `segment_document_layered()` call path, not just the
standalone POC scripts, before this is considered proven.
