"""_find_act_name() only recognized "...Act" names, so every IPC/CrPC/CPC
section citation -- extremely common in criminal filings, since none of
those three statutes' proper names contain the word "Act" -- permanently
showed "Act not named nearby" in the Provisions tab, even right next to
"Section 306 of the IPC". Found reviewing a real generated report against
its source judgment, 2026-09-11.
"""

from casemap_service import _find_act_name


def test_code_named_statute_is_found():
    window = "registered under Section 306 of the Indian Penal Code, 1860 against the accused"
    assert _find_act_name(window) == "Indian Penal Code, 1860"


def test_bare_ipc_acronym_is_resolved():
    window = "FIR No. 153/2017 registered under Section 306 of the IPC at P.S. Sarojini Nagar"
    assert _find_act_name(window) == "Indian Penal Code, 1860"


def test_bare_crpc_acronym_is_resolved():
    window = "closure report under Section 173 Cr.P.C. was accepted by the ld. ACJM"
    assert _find_act_name(window) == "Code of Criminal Procedure, 1973"


def test_act_named_statute_still_works():
    window = "for the purpose of admission as an advocate under Section 49 of the Advocates Act, 1961"
    assert _find_act_name(window) == "Advocates Act, 1961"


def test_no_statute_nearby_still_returns_none():
    assert _find_act_name("no statute mentioned anywhere in this text at all") is None


def test_quoted_statutory_clause_ending_in_act_is_not_mistaken_for_the_act_name():
    """General failure mode: a judgment quoting a statute's OWN text
    verbatim often contains a lowercase clause that happens to end in the
    literal word "Act" ("...recognised for the purpose of admission as an
    advocate under this Act"). _ACT_IN_SPAN is case-insensitive so it
    matches that clause too -- it must be rejected (no real, capitalized
    Act name in it), not returned as the resolved Act."""
    window = ('foreign qualifications in law which shall be recognised '
               'for the purpose of admission as an advocate under this Act; '
               'thus, it is in exercise of these powers under Section 49 of '
               'the Act of 1961, that the council prescribes standards')
    assert _find_act_name(window) is None


def test_real_act_name_still_found_even_when_a_quoted_clause_precedes_it():
    """When the window has BOTH a false-positive lowercase clause AND a
    real, properly capitalized Act name, the real one must still be found
    -- rejecting the first candidate must not give up on the whole window."""
    window = ('recognised for the purpose of admission as an advocate under '
               'this Act; thus it is exercised under Section 49 of the '
               'Advocates Act, 1961, in furtherance of these powers')
    assert _find_act_name(window) == "Advocates Act, 1961"
