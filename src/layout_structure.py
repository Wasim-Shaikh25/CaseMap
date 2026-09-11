"""layout_structure.py — Docling-backed structure detection with honest degrade.

Implements the seam casemap_pipeline.segment_document_layered() already calls.
Docling is optional: not installed / convert raises / zero headings all fall
through to casemap_pipeline.detect_structure + segment_document. Page numbers
are 1-indexed (docs/requirements/2026-09-09-structure-and-embedding-layers/T1_RESULTS.md).
Docling is not a requirements.txt pin (HANDOFF §9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayeredStructureResult:
    sections: list[dict]
    tier: str
    confidence: str
    tier_reason: str
    stats: dict = field(default_factory=dict)


def _is_section_header(item: Any) -> bool:
    # Docling 2.x uses DocItemLabel.SECTION_HEADER; str() is not always
    # exactly "section_header". T1 matched on substring.
    return "section_header" in str(getattr(item, "label", "")).lower()


def _legacy(pages: list[dict], toc: list | None, tier: str, reason: str) -> LayeredStructureResult:
    from casemap_pipeline import detect_structure, segment_document
    signals = detect_structure(pages, toc or [])
    return LayeredStructureResult(
        segment_document(pages, signals), tier, "unknown", reason, signals,
    )


def _load_converter():
    from docling.document_converter import DocumentConverter
    return DocumentConverter


def detect_structure_layered(pdf_path: str, pages: list[dict],
                             toc: list | None = None) -> LayeredStructureResult:
    try:
        DocumentConverter = _load_converter()
    except ImportError:
        return _legacy(pages, toc, "legacy_fallback_internal", "docling not installed")

    try:
        result = DocumentConverter().convert(pdf_path)
        headings = []
        for item, _level in result.document.iterate_items():
            if not _is_section_header(item):
                continue
            prov = getattr(item, "prov", None) or []
            if not prov:
                continue
            page_no = getattr(prov[0], "page_no", None)
            text = (getattr(item, "text", "") or "").strip()
            if page_no is None or not text:
                continue
            headings.append({"page": int(page_no), "text": text})
    except Exception as e:
        return _legacy(
            pages, toc, "legacy_fallback_docling_error", f"docling raised: {e}",
        )

    if not headings:
        return _legacy(
            pages, toc, "legacy_fallback_no_headings",
            "docling found no section_header items",
        )

    from casemap_pipeline import _segment_by_headings
    sections = _segment_by_headings(pages, headings)
    return LayeredStructureResult(
        sections, "docling_layout", "high",
        f"docling found {len(headings)} headings",
        {"heading_count": len(headings)},
    )
