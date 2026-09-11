"""BETWEEN...AND tribunal captions (no VERSUS) must still yield parties.

Found on a real filed NGT appeal (2026-09-11, F-22) fetched from a public
source (casi.sas.upenn.edu) while checking how the pipeline handles document
types outside testdata/ — it returned ZERO parties despite a clean, real
multi-party caption. The excerpt below is the real caption block (cause
title only, not the 43-page appeal body) — public tribunal filing, quoted
for structural testing, not the substantive content of the case.
"""

from document_profile import extract_parties_hybrid, extract_parties_layered

NGT_CAPTION = """Page 1 of 43

BEFORE THE NATIONAL GREEN TRIBUNAL,
NEW DELHI
(PRINCIPAL BENCH)

Monday the 12th day of September 2011

Appeal No. 3 of 2011


Quorum:
1. Hon'ble Justice C.V. Ramulu
(Judicial Member)
2. Hon'ble Dr. Devendra Kumar Agrawal
(Expert Member)


BETWEEN:

1. The Sarpanch,
Grampanchayat Tiroda,
Tal. Sawantwadi,
District Sindhudurg,
Maharashtra

2. Mr. Ajay Shivajirao Bhonsle,
Khashewadi, Tiroda,
Tal. Sawantwadi,
District Sindhudurg,
Maharashtra

.....Appellants.

AND

1. The Ministry of Environment and Forests,
Through its Principal Secretary,
Government of India,
CGO Complex, Lodi Road,
New Delhi - 110 003

2. Maharashtra State Pollution Control Board,
Through Secretary,
Kalptaru Point, Mumbai - 400 022

.....Respondents.
"""


def _names_roles(result):
    return [(p.name, p.role) for p in result.parties]


def test_between_and_caption_finds_both_sides():
    r = extract_parties_layered(NGT_CAPTION, "ngt_appeal.txt")
    joined = " | ".join(p.name for p in r.parties).casefold()
    assert "sarpanch" in joined
    assert "ajay shivajirao bhonsle" in joined
    assert "ministry of environment" in joined
    assert "maharashtra state pollution control board" in joined


def test_between_and_caption_roles_from_case_type():
    r = extract_parties_layered(NGT_CAPTION, "ngt_appeal.txt")
    roles = dict(_names_roles(r))
    assert roles["The Sarpanch"] == "Appellant"
    assert roles["Mr. Ajay Shivajirao Bhonsle"] == "Appellant"
    assert roles["The Ministry of Environment and Forests"] == "Respondent"


def test_between_and_caption_survives_a_mid_block_page_break():
    """A page-break line ('Page N of M') landing mid-block (a real PDF
    extraction artifact, not part of the caption) must not truncate the
    block or become a fake party."""
    text = NGT_CAPTION.replace(
        "2. Mr. Ajay Shivajirao Bhonsle,",
        "\nPage 2 of 43\n\n2. Mr. Ajay Shivajirao Bhonsle,",
    )
    r = extract_parties_layered(text, "ngt_appeal.txt")
    joined = " | ".join(p.name for p in r.parties).casefold()
    assert "ajay shivajirao bhonsle" in joined
    assert not any("page 2 of 43" in p.name.casefold() for p in r.parties)


def test_ordinary_prose_and_is_not_mistaken_for_a_caption_separator():
    """No BETWEEN line present -- a document that just happens to contain
    the word 'AND' on its own short line must not spuriously anchor a
    caption split."""
    text = "IN THE HIGH COURT OF BOMBAY\nSome heading\nAND\nmore text\n"
    r = extract_parties_layered(text, "plain.txt")
    assert r.parties == []


def test_between_and_caption_hybrid_wrapper_no_ml():
    r = extract_parties_hybrid(NGT_CAPTION, "ngt_appeal.txt", nlp=None, allow_degraded=True)
    joined = " | ".join(p.name for p in r.parties).casefold()
    assert "sarpanch" in joined
    assert "ministry of environment" in joined
