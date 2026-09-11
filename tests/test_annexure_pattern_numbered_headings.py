"""ANNEXURE_PATTERN previously only matched a bare heading word ("PRAYER",
"GROUNDS") with no numbering prefix -- real filed petitions almost always
number these sections ("VII. GROUNDS", "XI. INTERIM PRAYER"), so the pattern
silently matched nothing on an actual petition. Found by running the pipeline
against a real Supreme Court writ petition (user-supplied, 2026-09-10) that
uses exactly this numbering convention throughout."""

from casemap_pipeline import ANNEXURE_PATTERN


def test_roman_numeral_prefixed_headings_match():
    for line in ["VII. GROUNDS", "VI. QUESTIONS OF LAW", "IV. SYNOPSIS"]:
        assert ANNEXURE_PATTERN.match(line), line


def test_interim_and_final_prayer_qualifiers_match():
    for line in ["XI. INTERIM PRAYER", "XII. FINAL PRAYER", "PRAYER", "PRAYER FOR RELIEF"]:
        assert ANNEXURE_PATTERN.match(line), line


def test_list_of_dates_and_events_variant_matches():
    assert ANNEXURE_PATTERN.match("LIST OF DATES AND EVENTS")
    assert ANNEXURE_PATTERN.match("LIST OF DATES")


def test_bare_headings_still_match_unchanged():
    for line in ["INDEX", "SYNOPSIS", "AFFIDAVIT", "VAKALATNAMA", "GROUNDS"]:
        assert ANNEXURE_PATTERN.match(line), line


def test_prose_mention_does_not_false_positive():
    """The word appearing mid-sentence must never match -- only a real
    standalone heading line."""
    assert not ANNEXURE_PATTERN.match(
        "This petition has been preferred, inter alia, with a prayer to quash")
    assert not ANNEXURE_PATTERN.match(
        "the grounds on which this challenge is mounted are as follows")
    assert not ANNEXURE_PATTERN.match(
        "Leave to appeal is sought for on the following grounds.")


def test_official_sc_form_headings_match():
    """Standalone heading lines from Supreme Court e-filing specimens
    (cdnbbsr.s3waas.gov.in WP format 2024011726 and SLP form 2024011763),
    measured 2026-09-10 — not lettered/parenthetical probes, which no real
    source in this session used."""
    for line in [
        "3. Grounds",
        "5. GROUNDS :",
        "6. GROUNDS FOR INTERIM RELIEF :",
        "7. MAIN PRAYER :",
        "8. INTERIM RELIEF :",
        "2. Question(s) of Law",
        "Question(s) of Law",
        "PRAYER",
    ]:
        assert ANNEXURE_PATTERN.match(line), line


def test_lettered_and_parenthetical_prefixes_still_unmatched():
    """HANDOFF §9.3 probes. No real petition in testdata/real_pdfs/official
    forms used these; do not expand the pattern for them without a real hit."""
    for line in ["A. GROUNDS", "A) GROUNDS", "(vii) GROUNDS", "(VII) GROUNDS"]:
        assert not ANNEXURE_PATTERN.match(line), line
