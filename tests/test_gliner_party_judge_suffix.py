"""GLiNER party judge must not drop a real name because of a trailing
"& Ors."/"& Anr." suffix, and must count multi-span coverage, not just a
single span's own size.

Found on a real filed SC writ petition (2026-09-11, F-22): the judge
returned ZERO entities for "N. RAM & ORS" (a real petitioner) while
correctly tagging "N. RAM" alone -- the suffix alone was enough to blank the
model's prediction. Separately, on a real NGT appeal caption, "The Sarpanch,
Grampanchayat Tiroda" split into two adjacent spans covering 94% of the
string combined, which the old any-single-span >=70% rule rejected.

Gated: skips cleanly if gliner/torch aren't installed or the model can't be
fetched (offline CI), matching this repo's existing pattern for optional-ML
tests (see test_party_ladder_header_furniture.py's *_if_model_loads tests).
"""

import pytest

import casemap_service as service


def _judge():
    try:
        model = service._get_gliner_model()
    except Exception as exc:
        pytest.skip(f"gliner not loadable: {exc}")
    if model is None:
        pytest.skip("gliner not loadable (see stderr for the real reason)")
    return service._judge_party_name


def test_ors_suffix_does_not_blank_a_real_name():
    judge = _judge()
    assert judge("N. RAM & ORS") is True


def test_anr_suffix_does_not_blank_a_real_name():
    judge = _judge()
    assert judge("Union of India & Anr") is True


def test_multi_span_name_counts_combined_coverage():
    judge = _judge()
    assert judge("The Sarpanch, Grampanchayat Tiroda") is True


def test_known_furniture_is_still_rejected():
    judge = _judge()
    assert judge("LIST OF DATES") is False
    assert judge("SYNOPSIS") is False


# "State of <State>" is a deterministic bypass (no model call at all -- see
# _GOVT_LITIGANT_RE), so these run unconditionally, not gated by _judge().
def test_state_of_x_is_a_deterministic_keep():
    """Found on a real NGT appeal (2026-09-11, F-22/F-23): GLiNER returns
    ZERO entities for "State of Maharashtra"/"State of Madhya Pradesh" even
    though "State of U.P." (the same pattern, abbreviated) judges fine --
    erratic enough on this one templated, unambiguous pattern that it gets a
    deterministic bypass instead."""
    assert service._judge_party_name("State of Maharashtra") is True
    assert service._judge_party_name("State of Madhya Pradesh") is True
    assert service._judge_party_name("Union of India") is True
    assert service._judge_party_name("Government of NCT of Delhi") is True


def test_state_of_x_bypass_does_not_swallow_furniture():
    judge = _judge()
    assert judge("LIST OF DATES") is False
