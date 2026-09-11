"""Amounts written in words (case_symbols.find_word_amounts) + the
AMOUNT_PATTERN comma-only false-positive fix.

Both were added while wiring the previously-unused amount_from_words() into
the product pipeline (server/app.py) and testing it against the real 22-doc
corpus — the corpus test surfaced the pre-existing "Rs," junk match.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from case_symbols import find_word_amounts
from casemap_pipeline import AMOUNT_PATTERN


def test_find_word_amounts_parses_rupees_in_words():
    hits = find_word_amounts("the sum of Rupees One Crore was paid")
    assert len(hits) == 1
    assert hits[0]["value"] == 10_000_000
    assert "one crore" in hits[0]["raw"].lower()
    # span must locate the phrase verbatim in the source
    s, e = hits[0]["span"]
    assert "Rupees One Crore" in "the sum of Rupees One Crore was paid"[s:e]


def test_find_word_amounts_requires_currency_and_scale():
    # a scale word with no currency anchor must NOT become an amount
    assert find_word_amounts("he waited a hundred years for justice") == []
    # a currency anchor with no parseable words must NOT become an amount
    assert find_word_amounts("a sum of Rs. ____ remained due") == []


def test_find_word_amounts_various_scales():
    assert find_word_amounts("Rs. Fifty Lakhs Only")[0]["value"] == 5_000_000
    assert find_word_amounts("INR Ten Thousand")[0]["value"] == 10_000


def test_amount_pattern_rejects_bare_comma():
    # the bug: "Rs.," and "Rs," (currency marker, no digits) used to match
    assert AMOUNT_PATTERN.findall("a sum of Rs. , was claimed") == []
    assert AMOUNT_PATTERN.findall("paid Rs, to the bank") == []


def test_amount_pattern_still_matches_real_figures():
    assert AMOUNT_PATTERN.search("Rs. 1,20,00,000") is not None
    assert AMOUNT_PATTERN.search("₹50,000") is not None
    assert AMOUNT_PATTERN.search("Rs. 5 crore") is not None
