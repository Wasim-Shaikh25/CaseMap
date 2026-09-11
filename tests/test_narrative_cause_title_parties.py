"""Suo motu / narrative cause titles ("COURT ON ITS OWN MOTION IN RE: ...")
name the moving party as one long descriptive phrase spanning several
ALL-CAPS lines, not a short name. extract_parties()/_group_entries() assume
one party per line and split it into one bogus "party" per line instead --
found 2026-09-11 on a real suo motu writ (W.P.(CRL) 793/2017), where the
narrative Petitioner recital plus interspersed section headings produced
10 fragment "parties", none of them real.

extract_parties_narrative_cause_title() is a separate function gated on a
suo-motu/narrative marker at the top of the block above VERSUS -- these
tests also confirm an ORDINARY two-party caption (same fixture used in
test_petition_cause_title_parties.py) is completely unaffected, since that
extractor is meant to be a no-op for every document that isn't this shape.
"""

from document_profile import extract_parties_layered

NARRATIVE_CAUSE_TITLE = """
IN THE HIGH COURT OF DELHI AT NEW DELHI

W.P.(CRL) 793/2017 & CRL.M.As.16639/2017, 8850/2024

COURT ON ITS OWN MOTION IN
RE: SUICIDE COMMITTED BY A STUDENT,
LAW STUDENT OF A UNIVERSITY                    .....Petitioner

versus

.......                                            .....Respondent

CORAM:
JUSTICE A
JUSTICE B

III(A). PROCEEDINGS IN THE WRIT PETITION

1. This petition raises the question of mandatory attendance norms.
"""

ORDINARY_TWO_PARTY_CAUSE_TITLE = """
IN THE SUPREME COURT OF INDIA
(CIVIL ORIGINAL JURISDICTION)

WRIT PETITION (CIVIL) NO. ________ OF 2026

IN THE MATTER OF:

A.B. Petitioner
S/o Test, Age about 30 years,
Indian citizen, residing at [FULL RESIDENTIAL ADDRESS],

...PETITIONER

VERSUS

1. BAR COUNCIL OF INDIA
    Through its Secretary, 21, Rouse Avenue, New Delhi.

...RESPONDENTS
"""


def test_narrative_petitioner_becomes_one_party_not_many_fragments():
    r = extract_parties_layered(NARRATIVE_CAUSE_TITLE, "suo_motu.txt")
    assert r.tier == "tier0_narrative_cause_title"
    petitioner_side = [p for p in r.parties if p.side == "A"]
    assert len(petitioner_side) == 1
    name = petitioner_side[0].name
    assert "SUICIDE COMMITTED BY A STUDENT" in name
    assert "LAW STUDENT OF A UNIVERSITY" in name
    # Section headings and case numbers below VERSUS must not leak in as
    # extra bogus parties the way line-by-line splitting produced before.
    all_names = " | ".join(p.name for p in r.parties)
    assert "PROCEEDINGS IN THE WRIT PETITION" not in all_names
    assert "793/2017" not in all_names


def test_ordinary_two_party_caption_is_unaffected():
    """The narrative extractor must be a strict no-op here -- same tier and
    same parties as before TIER 0 existed."""
    r = extract_parties_layered(ORDINARY_TWO_PARTY_CAUSE_TITLE, "ordinary_wp.txt")
    assert r.tier == "tier1_cause_title"
    names = [p.name for p in r.parties]
    assert "BAR COUNCIL OF INDIA" in names
