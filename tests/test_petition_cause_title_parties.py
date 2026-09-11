"""Petition-shaped cause title: numbered respondents, paper-book furniture.

Structure copied from the real 2026-09-10 filed writ (F-12 / HANDOFF §9.2)
with public respondent names only — personal petitioner identity not used.
Re-validated after the fix against that same real filing in
temp/2026-09-10-petition-followups/ (not testdata/).
"""

import pytest

from document_profile import (
    _is_caption_furniture_name,
    extract_parties_hybrid,
    extract_parties_layered,
)
from case_symbols import normalize_name

CAUSE_TITLE = """
IN THE SUPREME COURT OF INDIA
(CIVIL ORIGINAL JURISDICTION)

WRIT PETITION (CIVIL) NO. ________ OF 2026

IN THE MATTER OF:

A.B. Petitioner
S/o Test, Age about 30 years,
Indian citizen, residing at [FULL RESIDENTIAL ADDRESS],
E-mail: _______________________ ; Mobile: __________________________.

...PETITIONER

VERSUS

1. BAR COUNCIL OF INDIA
    Through its Secretary, 21, Rouse Avenue Institutional Area, Near Bal Bhawan, New Delhi – 110 002.

2. UNION OF INDIA
    Through the Secretary, Ministry of Law and Justice, Shastri Bhawan, New Delhi – 110 001.

3. UNIVERSITY GRANTS COMMISSION
    Through its Secretary, Bahadur Shah Zafar Marg, New Delhi – 110 002.

...RESPONDENTS

COUNSEL FOR PETITIONER: Test
ADVOCATE-ON-RECORD: Test

PAPER BOOK
(FOR INDEX KINDLY SEE INSIDE)

INDEX
"""


def test_layered_stops_before_paper_book_and_keeps_numbered_respondents():
    r = extract_parties_layered(CAUSE_TITLE, "sample_wp.txt")
    names = " | ".join(p.name for p in r.parties)
    roles_by_name = {p.name: (p.role, p.side) for p in r.parties}
    assert "PAPER BOOK" not in names
    assert "E-mail" not in names
    assert "BAR COUNCIL OF INDIA" in names
    assert "UNION OF INDIA" in names
    assert "UNIVERSITY GRANTS COMMISSION" in names
    assert roles_by_name["BAR COUNCIL OF INDIA"][1] == "B"
    assert roles_by_name["UNION OF INDIA"][1] == "B"
    assert roles_by_name["UNIVERSITY GRANTS COMMISSION"][1] == "B"


def test_furniture_names_cover_petition_section_labels():
    for n in ("INDEX", "SYNOPSIS", "LIST OF DATES", "PAPER BOOK", "VERSUS",
              "Nature of Matter"):
        assert _is_caption_furniture_name(n), n
    assert _is_caption_furniture_name(
        "Indian Council of Legal Aid & Advice v. Bar Council of India (1995) 1 SCC 732")
    assert not _is_caption_furniture_name("BAR COUNCIL OF INDIA")


def test_normalize_name_collapses_bci_aliases():
    assert normalize_name("BAR COUNCIL OF INDIA") == normalize_name(
        "the Bar Council of India")


def test_hybrid_drops_section_labels_if_model_loads():
    try:
        import spacy
        nlp = spacy.load("en_legal_ner_sm")
    except Exception as exc:
        pytest.skip(f"en_legal_ner_sm not loadable: {exc}")
    r = extract_parties_hybrid(CAUSE_TITLE, "sample_wp.txt", nlp=nlp)
    names = {p.name.strip().casefold() for p in r.parties}
    assert "index" not in names
    assert "paper book" not in names
    assert "versus" not in names
