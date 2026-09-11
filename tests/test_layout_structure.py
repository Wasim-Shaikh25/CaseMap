"""T2: layout_structure.detect_structure_layered degrade paths + optional real PDF."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from layout_structure import detect_structure_layered
from casemap_pipeline import segment_document_layered

PDF = (
    Path(__file__).resolve().parent.parent
    / "temp" / "2026-09-09-layer-additions-poc" / "pdfs"
    / "09_insolvency_nclat_singhania_v_bank_of_baroda.pdf"
)

PAGES = [
    {"page_number": 1, "text": "JUDGMENT\nIN THE MATTER OF\n", "page_kind": "digital", "words": []},
    {"page_number": 2, "text": "Further facts of the appeal.\n", "page_kind": "digital", "words": []},
]


def test_degrade_when_docling_not_installed():
    with patch("layout_structure._load_converter", side_effect=ImportError("forced")):
        r = detect_structure_layered("missing.pdf", PAGES, [])
    assert r.tier == "legacy_fallback_internal"
    assert r.sections
    assert all("section_label" in s and "pages" in s for s in r.sections)


def test_degrade_when_docling_raises():
    class Boom:
        def convert(self, _path):
            raise RuntimeError("convert failed")

    with patch("layout_structure._load_converter", return_value=Boom):
        r = detect_structure_layered("x.pdf", PAGES, [])
    assert r.tier == "legacy_fallback_docling_error"
    assert "convert failed" in r.tier_reason
    assert r.sections


def test_degrade_when_docling_finds_zero_headings():
    empty_doc = SimpleNamespace(iterate_items=lambda: iter([]))
    conv_result = SimpleNamespace(document=empty_doc)

    class Empty:
        def convert(self, _path):
            return conv_result

    with patch("layout_structure._load_converter", return_value=Empty):
        r = detect_structure_layered("x.pdf", PAGES, [])
    assert r.tier == "legacy_fallback_no_headings"
    assert r.sections


def test_docling_headings_use_page_no_as_is():
    """T1: page_no is 1-indexed; do not subtract 1."""
    items = [
        (SimpleNamespace(
            label="SECTION_HEADER",
            text="FACTS",
            prov=[SimpleNamespace(page_no=2)],
        ), 0),
    ]
    fake_doc = SimpleNamespace(iterate_items=lambda: iter(items))
    conv_result = SimpleNamespace(document=fake_doc)

    class Fake:
        def convert(self, _path):
            return conv_result

    with patch("layout_structure._load_converter", return_value=Fake):
        r = detect_structure_layered("x.pdf", PAGES, [])
    assert r.tier == "docling_layout"
    assert r.confidence == "high"
    assert r.stats["heading_count"] == 1
    labels = [s["section_label"] for s in r.sections]
    assert "FACTS" in labels
    facts = next(s for s in r.sections if s["section_label"] == "FACTS")
    assert facts["pages"][0]["page_number"] == 2


def test_real_pdf_through_segment_document_layered():
    if not PDF.is_file():
        pytest.skip("T1 fixture PDF missing")
    try:
        import fitz
    except ImportError:
        pytest.skip("pymupdf not installed")
    try:
        import docling.document_converter  # noqa: F401
    except ImportError:
        pytest.skip("docling not installed")

    doc = fitz.open(str(PDF))
    pages = []
    for i, page in enumerate(doc):
        pages.append({
            "page_number": i + 1,
            "text": page.get_text("text"),
            "page_kind": "digital",
            "words": [],
        })
    doc.close()
    sections, meta = segment_document_layered(str(PDF), pages, [])
    assert sections
    assert meta["tier"] in (
        "docling_layout",
        "legacy_fallback_no_headings",
        "legacy_fallback_docling_error",
        "legacy_fallback_internal",
        "legacy_text_patterns",
    )
    if meta["tier"] == "docling_layout":
        assert meta["confidence"] == "high"
        assert any(s.get("detected") for s in sections)
