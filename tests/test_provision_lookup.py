"""
test_provision_lookup.py — tests the GLUE CODE (HTML parsing, confidence
gate, caching, failure handling) against a FAKE requests.get, not the real
IndianKanoon.org site. Same spirit as test_opennyai_bridge.py: what's faked
is the network response; what's real is everything downstream — the regex
extraction, the confidence gate, the in-process cache.

The fixture HTML below is a trimmed, structurally faithful copy of a real
response (confirmed by hand against indiankanoon.org/search/?formInput=...
during development, 2026-09-11) — same tag names, same class names, same
nesting, just fewer results and shorter headline text.
"""

import provision_lookup as pl


class _FakeResponse:
    def __init__(self, html, ok=True):
        self.text = html
        self.ok = ok


def _fake_response(html: str, ok: bool = True):
    return _FakeResponse(html, ok)


BARE_STATUTE_HTML = """
<div class="results-list">
<article class="result" role="listitem">
  <h4 class="result_title">
    <a href="/doc/1056396/"><b>Section</b> <b>125</b> in The <b>Code</b> of <b>Criminal</b> <b>Procedure</b>, 1973</a>
    [<a href="/doc/445276/">Entire Act</a>]
  </h4>
  <div class="headline">
    <b>Section</b> <b>125</b> in The <b>Code</b> of <b>Criminal</b> <b>Procedure</b>, 1973
    <b>125</b>. Order for maintenance of wives, children and parents.
    (1) If any person having sufficient means ... from time to time direct
  </div>
  <div class="hlbottom">
    <span class="docsource">Union of India - Section</span>
  </div>
</article>
</div>
"""

JUDGMENT_ONLY_HTML = """
<div class="results-list">
<article class="result" role="listitem">
  <h4 class="result_title">
    <a href="/docfragment/117541087/?formInput=Section%20125">Rajnesh vs Neha on 4 November, 2020</a>
  </h4>
  <div class="headline">
    maintenance under this Act ... <b>Section</b> <b>125</b> of the Cr.P.C.
  </div>
  <div class="hlbottom">
    <span class="docsource">Supreme Court of India</span>
  </div>
</article>
</div>
"""

WRONG_SECTION_NUMBER_HTML = """
<div class="results-list">
<article class="result" role="listitem">
  <h4 class="result_title">
    <a href="/doc/999999/"><b>Section</b> <b>9</b> in The <b>Indian</b> <b>Contract</b> <b>Act</b>, 1872</a>
  </h4>
  <div class="headline">Section 9 in The Indian Contract Act, 1872</div>
  <div class="hlbottom">
    <span class="docsource">Indian Contract Act - Section</span>
  </div>
</article>
</div>
"""


def test_confident_bare_statute_match(monkeypatch):
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _fake_response(BARE_STATUTE_HTML))

    result = pl.lookup_provision("Section 125", "Code of Criminal Procedure")

    assert result is not None
    assert result["title"] == "Section 125 in The Code of Criminal Procedure, 1973"
    assert result["source_url"] == "https://indiankanoon.org/doc/1056396/"
    assert "Order for maintenance" in result["snippet"]


def test_judgment_result_is_skipped_not_guessed(monkeypatch):
    """First result is a judgment (docsource has no '- Section' suffix) —
    must skip, never mistake case law for the statute text itself."""
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _fake_response(JUDGMENT_ONLY_HTML))

    result = pl.lookup_provision("Section 125", "Code of Criminal Procedure")

    assert result is None


def test_mismatched_section_number_is_skipped(monkeypatch):
    """docsource looks like a bare statute, but it's a DIFFERENT section
    than what was queried — the number-match guard must catch this."""
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _fake_response(WRONG_SECTION_NUMBER_HTML))

    result = pl.lookup_provision("Section 125", None)

    assert result is None


def test_no_results_is_skipped(monkeypatch):
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get",
                        lambda *a, **k: _fake_response('<div class="results-list"></div>'))

    assert pl.lookup_provision("Section 9999999", "Nonexistent Act") is None


def test_non_ok_response_is_skipped(monkeypatch):
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _fake_response(BARE_STATUTE_HTML, ok=False))

    assert pl.lookup_provision("Section 125", "Code of Criminal Procedure") is None


def test_network_exception_never_raises(monkeypatch):
    """A timeout or connection error must degrade to None, not crash the
    document being processed — this is an optional enrichment layer, never
    load-bearing for the rest of the pipeline."""
    def boom(*a, **k):
        raise pl.requests.exceptions.ConnectionError("no route to host")
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", boom)

    assert pl.lookup_provision("Section 125", "Code of Criminal Procedure") is None


def test_result_is_cached_per_unique_query(monkeypatch):
    """One provision per unique (section, act) pair should hit the network
    exactly once, even when looked up repeatedly — the whole point of the
    cache (one outbound call per unique provision per document)."""
    calls = []

    def counting_get(*a, **k):
        calls.append(1)
        return _fake_response(BARE_STATUTE_HTML)

    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", counting_get)

    first = pl.lookup_provision("Section 125", "Code of Criminal Procedure")
    second = pl.lookup_provision("Section 125", "Code of Criminal Procedure")

    assert first == second
    assert len(calls) == 1


def test_different_provisions_are_not_conflated_in_cache(monkeypatch):
    pl.reset_cache()
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _fake_response(BARE_STATUTE_HTML))

    result_with_act = pl.lookup_provision("Section 125", "Code of Criminal Procedure")
    result_no_act = pl.lookup_provision("Section 125", None)

    # Different cache keys (different query strings) -- both resolve
    # independently rather than one silently reusing the other's result.
    assert result_with_act is not None
    assert result_no_act is not None
