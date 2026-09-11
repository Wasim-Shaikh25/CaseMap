"""Per-page PDF headings plus two headings on one physical page.

HANDOFF §9.4: F-12's in-page split was only proven on one-page .txt.
This round-trips heading lines through PyMuPDF extract_pages (digital text
layer — not OCR). Body sentences are filler; the heading strings are the
F-12 petition vocabulary.
"""

from pathlib import Path

import fitz

from casemap_pipeline import detect_structure, extract_pages, segment_document


def test_extract_pages_splits_two_headings_on_one_pdf_page(tmp_path: Path):
    page1 = "INDEX\nCover index listing the paper-book contents for the filing.\n"
    page2 = (
        "AFFIDAVIT\n"
        "I, the deponent, do hereby solemnly affirm that the facts in the "
        "accompanying petition are true to my knowledge.\n\n"
        "VAKALATNAMA\n"
        "I appoint the advocate-on-record to appear and act in this matter.\n"
    )
    pdf = tmp_path / "petition_pages.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 72), page1, fontsize=11)
    p = doc.new_page()
    p.insert_text((72, 72), page2, fontsize=11)
    doc.save(pdf)
    doc.close()

    got = extract_pages(str(pdf), ocr_engine="tesseract")
    assert len(got["pages"]) == 2
    assert all(p["page_kind"] == "digital" for p in got["pages"])
    sig = detect_structure(got["pages"], got["toc"])
    labels = [h["text"] for h in sig["headings"]]
    assert "INDEX" in labels
    assert "AFFIDAVIT" in labels
    assert "VAKALATNAMA" in labels
    same_page = [h for h in sig["headings"] if h["page"] == 2]
    assert len(same_page) == 2
    assert same_page[0]["offset"] < same_page[1]["offset"]

    sections = segment_document(got["pages"], sig)
    sec_labels = [s["section_label"] for s in sections]
    assert "AFFIDAVIT" in sec_labels
    assert "VAKALATNAMA" in sec_labels
    aff = next(s for s in sections if s["section_label"] == "AFFIDAVIT")
    vak = next(s for s in sections if s["section_label"] == "VAKALATNAMA")
    aff_text = "".join(p["text"] for p in aff["pages"])
    vak_text = "".join(p["text"] for p in vak["pages"])
    assert "solemnly affirm" in aff_text
    assert "appoint" not in aff_text
    assert "appoint" in vak_text
