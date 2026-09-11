"""Running page footers and e-signature stamps fuse onto real sentences in
PyMuPDF's reading order on Indian court e-filings, corrupting chronology/
key-point excerpts (e.g. "...fulfil all Digitally Signed", "W.P.(CRL)
793/2017 Page 92 of 122 norms required..."). Found reviewing a real
CaseMap-generated report against its 122-page source judgment, 2026-09-11.
"""

from casemap_pipeline import _strip_page_furniture


def test_footer_fused_before_sentence_is_removed():
    text = "W.P.(CRL) 793/2017 Page 92 of 122 norms required in most institutions."
    cleaned = _strip_page_furniture(text)
    assert "Page 92 of 122" not in cleaned
    assert "norms required in most institutions." in cleaned


def test_footer_fused_after_sentence_is_removed():
    text = "case of 3 year law courses, the attendance requirements were almost identical. W.P.(CRL) 793/2017 Page 92 of 122"
    cleaned = _strip_page_furniture(text)
    assert "Page" not in cleaned
    assert "attendance requirements were almost identical." in cleaned


def test_digitally_signed_with_name_is_removed():
    text = "office order dated 4th September, Digitally Signed By:KESHAV Kumar"
    cleaned = _strip_page_furniture(text)
    assert "Digitally Signed" not in cleaned
    assert "office order dated 4th September," in cleaned


def test_bare_digitally_signed_is_removed():
    text = "fulfil all Digitally Signed obligations under the regulations."
    cleaned = _strip_page_furniture(text)
    assert "Digitally Signed" not in cleaned


def test_ordinary_prose_is_untouched():
    text = "The Court held that mandatory attendance norms need to be reconsidered."
    assert _strip_page_furniture(text) == text
