"""
test_provision_lookup.py — tests the GLUE CODE (local-index fuzzy matching,
JSON parsing, caching, failure handling) against a FAKE requests.get and a
tiny FAKE local acts index, not the real indiacode.ecourtsindia.com site or
the real 836-row src/indiacode_acts.json.

Same spirit as test_opennyai_bridge.py: what's faked is the network response
and the local index; what's real is everything downstream — the act-name
fuzzy match, the section-number extraction, the confidence threshold, the
in-process cache.
"""

import provision_lookup as pl

FAKE_ACTS = [
    {"id": "crpc", "short_title": "The Code of Criminal Procedure, 1973", "act_year": 1973},
    {"id": "pc-act-1988", "short_title": "The Prevention of Corruption Act, 1988", "act_year": 1988},
    {"id": "dv-act", "short_title": "The Protection of Women from Domestic Violence Act, 2005", "act_year": 2005},
    {"id": "companies-act-1956", "short_title": "The Companies Act, 1956", "act_year": 1956},
    {"id": "companies-act-2013", "short_title": "The Companies Act, 2013", "act_year": 2013},
]


class _FakeResponse:
    def __init__(self, json_body, ok=True):
        self._json = json_body
        self.ok = ok

    def json(self):
        return self._json


SECTION_125_OK = {
    "act": {"short_title": "The Code of Criminal Procedure, 1973", "in_force": True},
    "section": {"number": "125", "text": "Order for maintenance of wives, children and parents. ..."},
    "url": "https://indiacode.ecourtsindia.com/crpc/section/125/",
}


def _patch_index(monkeypatch, acts=FAKE_ACTS):
    monkeypatch.setattr(pl, "_ACTS_INDEX", list(acts))


def test_confident_match_returns_verbatim_text(monkeypatch):
    pl.reset_cache()
    _patch_index(monkeypatch)
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _FakeResponse(SECTION_125_OK))

    result = pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973")

    assert result is not None
    assert result["text"].startswith("Order for maintenance")
    assert result["source_url"] == "https://indiacode.ecourtsindia.com/crpc/section/125/"
    assert result["in_force"] is True
    assert "Code of Criminal Procedure" in result["title"]


def test_truncated_act_name_still_resolves_via_fuzzy_match(monkeypatch):
    """A truncated act name (as _find_act_name()'s regex often produces,
    e.g. "Corruption Act, 1988" for "The Prevention of Corruption Act,
    1988") must still resolve locally -- the whole point of fuzzy matching
    against the bundled index instead of requiring an exact string."""
    pl.reset_cache()
    _patch_index(monkeypatch)
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _FakeResponse({
        "act": {"short_title": "The Prevention of Corruption Act, 1988", "in_force": True},
        "section": {"number": "7", "text": "Offence relating to public servant being bribed."},
        "url": "https://indiacode.ecourtsindia.com/pc-act-1988/section/7/",
    }))

    result = pl.lookup_provision("Section 7", "Corruption Act, 1988")

    assert result is not None
    assert "Offence relating to public servant" in result["text"]


def test_year_disambiguates_same_named_acts(monkeypatch):
    """Two Acts can share almost the same name across different years
    (Companies Act 1956 vs 2013) -- the year in the citation must pick the
    right one, confirmed by which slug gets requested."""
    pl.reset_cache()
    _patch_index(monkeypatch)
    requested = []

    def fake_get(url, **kwargs):
        requested.append(url)
        return _FakeResponse({
            "act": {"short_title": "The Companies Act, 2013", "in_force": True},
            "section": {"number": "2", "text": "Definitions."},
            "url": "https://indiacode.ecourtsindia.com/companies-act-2013/section/2/",
        })

    monkeypatch.setattr(pl.requests, "get", fake_get)
    pl.lookup_provision("Section 2", "Companies Act, 2013")

    assert requested and "companies-act-2013" in requested[0]


def test_year_in_citation_differs_from_index_act_year_still_resolves(monkeypatch):
    """The year in a citation is the year people actually cite (usually
    enactment); the bundled index's `act_year` field can instead be a
    commencement/in-force year for the same Act, e.g. real-world CrPC is
    indexed with act_year 1974 (came into force) even though every filing
    cites "..., 1973" (enacted). The year-filtered candidate pool must not
    be trusted blindly -- when it excludes the right Act and the match
    fails, retry against the full index before giving up.
    """
    pl.reset_cache()
    _patch_index(monkeypatch, acts=[
        {"id": "crpc", "short_title": "The Code of Criminal Procedure, 1973", "act_year": 1974},
        {"id": "some-other-1973-act", "short_title": "The Unrelated Act, 1973", "act_year": 1973},
    ])
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _FakeResponse(SECTION_125_OK))

    result = pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973")

    assert result is not None
    assert "Order for maintenance" in result["text"]


def test_no_act_name_skips_without_any_network_call(monkeypatch):
    """A citation-to-statute tool needs the Act, not just a section number
    -- a bare 'Section 125' with nothing nearby must not guess."""
    pl.reset_cache()
    _patch_index(monkeypatch)
    calls = []
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: calls.append(1))

    result = pl.lookup_provision("Section 125", None)

    assert result is None
    assert calls == []


def test_unresolvable_act_skips_without_any_network_call(monkeypatch):
    """An Act name with no confident match in the local index (a State Act,
    or an Act outside the bundled 836) must skip locally -- never a second
    'let's search for it' network round-trip."""
    pl.reset_cache()
    _patch_index(monkeypatch)
    calls = []
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: calls.append(1))

    result = pl.lookup_provision("Section 5", "Some Entirely Fictional Statute, 1999")

    assert result is None
    assert calls == []


def test_section_not_found_is_skipped(monkeypatch):
    pl.reset_cache()
    _patch_index(monkeypatch)
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _FakeResponse(
        {"error": "not_found"}, ok=False))

    assert pl.lookup_provision("Section 9999", "Code of Criminal Procedure, 1973") is None


def test_network_exception_never_raises(monkeypatch):
    """A timeout or connection error must degrade to None, not crash the
    document being processed — this is an optional enrichment layer, never
    load-bearing for the rest of the pipeline."""
    def boom(*a, **k):
        raise pl.requests.exceptions.ConnectionError("no route to host")
    pl.reset_cache()
    _patch_index(monkeypatch)
    monkeypatch.setattr(pl.requests, "get", boom)

    assert pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973") is None


def test_malformed_json_never_raises(monkeypatch):
    pl.reset_cache()
    _patch_index(monkeypatch)

    class _BadJson(_FakeResponse):
        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _BadJson({}))

    assert pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973") is None


def test_result_is_cached_per_unique_query(monkeypatch):
    """One provision per unique (section, act) pair should hit the network
    exactly once, even when looked up repeatedly."""
    pl.reset_cache()
    _patch_index(monkeypatch)
    calls = []

    def counting_get(*a, **k):
        calls.append(1)
        return _FakeResponse(SECTION_125_OK)

    monkeypatch.setattr(pl.requests, "get", counting_get)

    first = pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973")
    second = pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973")

    assert first == second
    assert len(calls) == 1


def test_different_provisions_are_not_conflated_in_cache(monkeypatch):
    pl.reset_cache()
    _patch_index(monkeypatch)
    monkeypatch.setattr(pl.requests, "get", lambda *a, **k: _FakeResponse(SECTION_125_OK))

    result_with_act = pl.lookup_provision("Section 125", "Code of Criminal Procedure, 1973")
    result_no_act = pl.lookup_provision("Section 125", None)

    assert result_with_act is not None
    assert result_no_act is None
