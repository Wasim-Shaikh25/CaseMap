"""_segment_by_headings() previously created one section boundary per PAGE,
not per heading. A .txt input loads its entire filing as a single page, so a
real petition's GROUNDS/PRAYER/AFFIDAVIT headings (all on page 1) collapsed
into one section labeled after whichever heading happened to be first --
found by running the pipeline against a real filed Supreme Court writ
petition (2026-09-10, not committed to the repo -- see CHANGELOG (36))."""

from casemap_pipeline import detect_structure, segment_document


def _page(text: str) -> dict:
    return {"page_number": 1, "text": text, "page_kind": "digital",
            "document": "x", "document_path": "x", "words": []}


def test_multiple_headings_on_one_page_become_separate_sections():
    text = (
        "SYNOPSIS\n"
        "This is the synopsis text explaining the background of the case "
        "in a few sentences for the court's convenience.\n\n"
        "VII. GROUNDS\n"
        "GROUND A: The impugned order has no rational nexus with the stated "
        "objective and imposes a disproportionate burden on the petitioner.\n\n"
        "XII. FINAL PRAYER\n"
        "It is respectfully prayed that this Hon'ble Court may be pleased to "
        "quash and set aside the impugned order in its entirety.\n"
    )
    pages = [_page(text)]
    signals = detect_structure(pages, [])
    sections = segment_document(pages, signals)

    labels = [s["section_label"] for s in sections]
    assert "SYNOPSIS" in labels
    assert "VII. GROUNDS" in labels
    assert "XII. FINAL PRAYER" in labels
    assert len(sections) == 3

    grounds = next(s for s in sections if s["section_label"] == "VII. GROUNDS")
    grounds_text = "".join(p["text"] for p in grounds["pages"])
    assert "GROUND A" in grounds_text
    assert "PRAYER" not in grounds_text  # real separation, not just a label change


def test_single_heading_per_page_behaves_as_before():
    """The common PDF case (Docling headings, one per physical page, no
    'offset' key) must be unaffected by this change."""
    pages = [
        {"page_number": 1, "text": "cover page text", "page_kind": "digital",
         "document": "x", "document_path": "x", "words": []},
        {"page_number": 2, "text": "JUDGMENT\nThe court finds as follows.",
         "page_kind": "digital", "document": "x", "document_path": "x", "words": []},
    ]
    headings = [{"page": 2, "text": "JUDGMENT"}]  # Docling shape: no "offset" key
    sections = segment_document(pages, {"mode": "structured", "headings": headings})
    assert len(sections) == 2
    assert sections[0]["section_label"] == "Document"
    assert sections[1]["section_label"] == "JUDGMENT"


def test_page_with_no_heading_still_works():
    pages = [_page("Plain text with no recognizable heading at all.")]
    signals = detect_structure(pages, [])
    sections = segment_document(pages, signals)
    assert len(sections) == 1
    assert sections[0]["pages"][0]["text"] == pages[0]["text"]
