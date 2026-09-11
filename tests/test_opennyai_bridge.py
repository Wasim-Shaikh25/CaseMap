"""
test_opennyai_bridge.py — tests the GLUE CODE, not the model.

Every entity below is hand-placed into REAL spacy.tokens.Doc / Span objects
via doc.char_span() and doc.set_ents() — the exact API the real
en_legal_ner_sm/trf model would populate. What is faked is the SOURCE of
those spans (a hand-written list instead of a forward pass); what is real
is everything downstream: ent.text, ent.label_, ent.start_char, ent.end_char,
and every line of opennyai_bridge.py / extract_parties_hybrid() that consumes
them.

This CANNOT prove the real model's accuracy. It proves that if the real
model returns spans shaped like these, the integration behaves correctly.
"""

import spacy

import opennyai_bridge as bridge
from document_profile import extract_parties_hybrid, extract_parties_layered


class FakeOpenNyAINLP:
    """Same call signature as a loaded spaCy model: nlp(text) -> Doc with
    .ents populated. Spans are supplied as (needle_text, label) pairs and
    located in whatever text is passed in — mimics a real model without
    hardcoding offsets, so the same fake works across several test texts.
    """
    def __init__(self, entity_specs: list[tuple[str, str]]):
        self._specs = entity_specs
        self._vocab_nlp = spacy.blank("en")

    def __call__(self, text: str):
        doc = self._vocab_nlp.make_doc(text)
        ents = []
        for needle, label in self._specs:
            idx = text.find(needle)
            if idx == -1:
                continue
            span = doc.char_span(idx, idx + len(needle), label=label,
                                 alignment_mode="expand")
            if span is not None:
                ents.append(span)
        doc.set_ents(ents)
        return doc


REAL_CRIMINAL_APPEAL = """REPORTABLE
IN THE SUPREME COURT OF INDIA
CRIMINAL APPELLATE JURISDICTION
CRIMINAL APPEAL NO. 2501 OF 2024
(Arising out of SLP (Crl.) No. 4241 of 2023)

SHAILESH KUMAR                              ... Appellant
                    VERSUS
STATE OF MAHARASHTRA & ANR.                 ... Respondents

JUDGMENT
"""

REAL_COMMERCIAL_SUIT = """IN THE HIGH COURT OF JUDICATURE AT BOMBAY
COMMERCIAL SUIT NO. 442 OF 2024

M/s Sunrise Infratech Private Limited,
                                                    ...Plaintiff
                        VERSUS

1. Meridian Constructions Pvt. Ltd.
                                                    ...Defendant No.1
"""


def run():
    passed = failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    print("=" * 72)
    print("TEST GROUP A — extract_parties_ml() against REAL spaCy Doc/Span API")
    print("=" * 72)
    fake = FakeOpenNyAINLP([("SHAILESH KUMAR", "PETITIONER"),
                            ("STATE OF MAHARASHTRA & ANR.", "RESPONDENT")])
    parties, meta = bridge.extract_parties_ml(REAL_CRIMINAL_APPEAL, fake)
    check("finds 2 parties", len(parties) == 2)
    check("side A = SHAILESH KUMAR",
          any(p.name == "SHAILESH KUMAR" and p.side == "A" for p in parties))
    check("side B = STATE OF MAHARASHTRA & ANR.",
          any("MAHARASHTRA" in p.name and p.side == "B" for p in parties))
    check("meta reports labels seen",
          meta["ner_labels_seen"] == ["PETITIONER", "RESPONDENT"])
    check("role is ML-generic before refinement",
          all(p.role in ("Petitioner", "Respondent") for p in parties))

    print("\n" + "=" * 72)
    print("TEST GROUP B — role REFINEMENT by deterministic case-type layer")
    print("=" * 72)
    # Same generic PETITIONER/RESPONDENT labels the model would emit for a
    # commercial suit -- the ML label set does not know "Plaintiff" exists.
    fake2 = FakeOpenNyAINLP([
        ("M/s Sunrise Infratech Private Limited", "PETITIONER"),
        ("Meridian Constructions Pvt. Ltd.", "RESPONDENT"),
    ])
    result = extract_parties_hybrid(REAL_COMMERCIAL_SUIT, "suit.pdf", nlp=fake2)
    check("tier is mandatory_ml_plus_case_type",
          result.tier == "mandatory_ml_plus_case_type")
    roles = {p.name.strip(): p.role for p in result.parties}
    check("Sunrise refined to Plaintiff (not generic Petitioner)",
          any(r == "Plaintiff" for n, r in roles.items() if "Sunrise" in n))
    check("Meridian refined to Defendant (not generic Respondent)",
          any(r == "Defendant" for n, r in roles.items() if "Meridian" in n))
    check("meta.ml_layer == active", result.meta.get("ml_layer") == "active")
    check("confidence is high", result.confidence == "high")

    print("\n" + "=" * 72)
    print("TEST GROUP C — MANDATORY raise when model genuinely unavailable")
    print("=" * 72)
    bridge.reset_cache()
    import spacy as _spacy
    real_load = _spacy.load
    _spacy.load = lambda name, *a, **k: (_ for _ in ()).throw(
        OSError(f"[E050] Can't find model '{name}'"))
    try:
        raised = False
        try:
            bridge.load_opennyai_ner("sm", allow_degraded=False)
        except bridge.ModelNotAvailableError as e:
            raised = True
            check("error message names the install command",
                  "pip install" in str(e))
        check("raises ModelNotAvailableError when required", raised)

        bridge.reset_cache()
        degraded = bridge.load_opennyai_ner("sm", allow_degraded=True)
        check("allow_degraded=True returns None instead of raising",
              degraded is None)
    finally:
        _spacy.load = real_load
        bridge.reset_cache()

    print("\n" + "=" * 72)
    print("TEST GROUP D — degraded-mode result is explicitly stamped")
    print("=" * 72)
    result_degraded = extract_parties_hybrid(REAL_CRIMINAL_APPEAL, "x.pdf",
                                             nlp=None, allow_degraded=True)
    check("tier is stamped DEGRADED_ prefix",
          result_degraded.tier.startswith("DEGRADED_"))
    check("meta.ml_layer == degraded",
          result_degraded.meta.get("ml_layer") == "degraded")
    check("deterministic ladder still found the real parties",
          {p.name for p in result_degraded.parties} >=
          {"SHAILESH KUMAR", "STATE OF MAHARASHTRA & ANR"})

    print("\n" + "=" * 72)
    print("TEST GROUP E — ML finds nothing -> falls through to full ladder")
    print("=" * 72)
    empty_fake = FakeOpenNyAINLP([])   # model ran, found zero entities
    result_e = extract_parties_hybrid(REAL_CRIMINAL_APPEAL, "x.pdf", nlp=empty_fake)
    check("tier is NOT the DEGRADED prefix (ML was active, just empty)",
          not result_e.tier.startswith("DEGRADED_"))
    check("meta notes ML active but empty",
          "ML layer active but found nothing" in result_e.meta.get("note", ""))
    check("deterministic ladder still recovered both parties",
          len(result_e.parties) == 2)

    print("\n" + "=" * 72)
    print("TEST GROUP F — regression: regex-only ladder unchanged")
    print("=" * 72)
    r = extract_parties_layered(REAL_COMMERCIAL_SUIT, "suit.pdf")
    check("regex-only ladder still works standalone",
          r.tier == "tier1_cause_title" and len(r.parties) == 2)

    print("\n" + "=" * 72)
    print(f"RESULT: {passed} passed, {failed} failed")
    print("=" * 72)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
