"""Numbered VERSUS-side party blocks with multi-line addresses must not
split the address onto its own fake party.

Found on real testdata/09_insolvency_nclat_singhania_v_bank_of_baroda.txt
(2026-09-11, F-22/F-23) while fixing the same bug on a fetched real NGT
appeal: "1. Bank of Baroda, / Through Its Senior Manager, / Zonal Stressed
Assets Recovery Branch / Located At: ... / Rajendra Place, New Delhi-110008"
was producing separate bogus parties for the address lines. The excerpt
below mirrors that real structure (not the real case's full text).
"""

from document_profile import extract_parties_layered

CAPTION = """IN THE MATTER OF:

Vijay Kumar Singhania                                          ... Appellant

Vs

1.  Bank of Baroda,
    Through Its Senior Manager,
    Zonal Stressed Assets Recovery Branch
    Located At: 4th Floor, Rajendra Bhawan,
    Rajendra Place, New Delhi-110008
2.  Sunil Kumar Gupta
    Interim Resolution Professional For Cygnus Splendid Limited
    B-10, Magnum House-1, Karampura Commercial Complex,
    Shivaji Marg, New Delhi, Delhi, 110015                    ... Respondents
"""


def test_numbered_block_address_lines_attach_to_their_entry():
    r = extract_parties_layered(CAPTION, "appeal.txt")
    names = [p.name.casefold() for p in r.parties]
    assert not any("through its senior manager" in n for n in names)
    assert not any("rajendra place" in n for n in names)
    assert not any("magnum house" in n for n in names)


def test_numbered_block_still_finds_both_numbered_parties():
    r = extract_parties_layered(CAPTION, "appeal.txt")
    joined = " | ".join(p.name for p in r.parties).casefold()
    assert "bank of baroda" in joined
    assert "sunil kumar gupta" in joined


def test_numbered_block_next_numbered_entry_still_starts_fresh():
    """The continuation default must not swallow entry 2 into entry 1's
    description -- a line matching the numbered-entry pattern always starts
    a new entry, even mid-block. Exactly 3 real parties in this caption:
    the unnumbered Appellant plus the 2 numbered Respondents."""
    r = extract_parties_layered(CAPTION, "appeal.txt")
    names = {p.name.casefold() for p in r.parties}
    assert names == {"vijay kumar singhania", "bank of baroda", "sunil kumar gupta"}
