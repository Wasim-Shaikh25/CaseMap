"""ML NER finding a party on only ONE side of a filing must not be trusted
outright as "the" party list.

General failure mode (not specific to any one document): the ML model scans
the first ~20k characters of the WHOLE document, not just the cause title,
so a name mentioned deep in body prose -- e.g. inside a court's verbatim
quote of an earlier order, affidavit, or settlement recital -- can get
spuriously tagged with a PETITIONER/RESPONDENT-style label. A real two-party
filing's genuine parties are essentially always tagged on BOTH sides, so a
lone one-sided ML hit is itself the signal something is wrong, regardless of
which document produced it. Reproduced here with a synthetic filing whose
real (two-sided, deterministically parseable) cause title has nothing to do
with the specific real judgment (Delhi HC, W.P.(CRL) 793/2017) that first
surfaced this failure mode, on 2026-09-11, by mistaking the deceased
student's father -- named only inside a quoted settlement recital on page
11 of 122 -- for "the Respondent" of a multi-institution suo motu case.
"""

import spacy

from document_profile import extract_parties_hybrid


class SequentialFakeNLP:
    """Place each (needle, label) at the next occurrence of needle."""

    def __init__(self, specs: list[tuple[str, str]]):
        self._specs = specs
        self._vocab_nlp = spacy.blank("en")

    def __call__(self, text: str):
        doc = self._vocab_nlp.make_doc(text)
        ents = []
        cursor = 0
        for needle, label in self._specs:
            idx = text.find(needle, cursor)
            if idx == -1:
                idx = text.find(needle)
            if idx == -1:
                continue
            span = doc.char_span(idx, idx + len(needle), label=label,
                                  alignment_mode="expand")
            if span is not None:
                ents.append(span)
            cursor = idx + max(len(needle), 1)
        doc.set_ents(ents)
        return doc


# A real, cleanly two-sided cause title the deterministic ladder can parse
# on its own (same shape already proven in test_petition_cause_title_parties.py).
GOOD_CAUSE_TITLE_TEXT = """
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
    Through its Secretary, 21, Rouse Avenue Institutional Area, Near Bal Bhawan, New Delhi - 110 002.

2. UNIVERSITY GRANTS COMMISSION
    Through its Secretary, Bahadur Shah Zafar Marg, New Delhi - 110 002.

...RESPONDENTS

JUDGMENT

1. This petition raises the question of mandatory attendance norms.

45. In an earlier, unrelated settlement recorded by consent, the family
of another student -- including Mr. Random Bystander -- agreed the case
be closed without further proceedings.
"""


def test_one_sided_ml_hit_falls_through_to_real_cause_title():
    """ML tags ONLY a stray RESPONDENT-side name found deep in body prose
    (the quoted settlement recital); it never tags anything on the
    Petitioner side. The real, two-sided cause title is right there at the
    top of the document and the deterministic ladder can parse it -- that
    must win, not the spurious single-sided ML guess.
    """
    nlp = SequentialFakeNLP([
        ("Mr. Random Bystander", "RESPONDENT"),
    ])
    result = extract_parties_hybrid(GOOD_CAUSE_TITLE_TEXT, "syn.txt", nlp=nlp)
    names = {p.name.strip() for p in result.parties}
    assert "Random Bystander" not in " ".join(names)
    assert any("BAR COUNCIL OF INDIA" in n for n in names)
    assert result.tier != "mandatory_ml_plus_case_type"


def test_one_sided_ml_hit_kept_as_partial_when_ladder_also_finds_nothing():
    """When even the deterministic ladder finds nothing (no locatable cause
    title at all), the incomplete-but-real ML hit is better than nothing --
    but it must be clearly marked as partial, not "high" confidence.
    """
    text = (
        "This is a short internal memo with no cause title or filing "
        "structure at all.\n\n"
        "45. In an earlier settlement, the family including Mr. Random "
        "Bystander agreed to close the matter.\n"
    )
    nlp = SequentialFakeNLP([
        ("Mr. Random Bystander", "RESPONDENT"),
    ])
    result = extract_parties_hybrid(text, "syn2.txt", nlp=nlp)
    assert result.tier == "ml_single_side_partial"
    assert result.confidence == "medium"
    assert len(result.parties) == 1


def test_two_sided_ml_hit_is_still_trusted_directly():
    """Sanity check the fix doesn't over-correct: a real two-sided ML
    result must still short-circuit straight to "mandatory_ml_plus_case_type"
    as before, without falling through to the ladder at all.
    """
    text = "IN THE HIGH COURT\nALICE CO Petitioner\nversus\nBOB CO Respondent\nJUDGMENT\n"
    nlp = SequentialFakeNLP([
        ("ALICE CO", "PETITIONER"),
        ("BOB CO", "RESPONDENT"),
    ])
    result = extract_parties_hybrid(text, "syn3.txt", nlp=nlp)
    assert result.tier == "mandatory_ml_plus_case_type"
    assert result.confidence == "high"
