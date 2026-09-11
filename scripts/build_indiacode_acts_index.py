"""build_indiacode_acts_index.py -- ONE-TIME, developer-run build script.

Fetches every Central Act's {id, short_title, act_year} from
indiacode.ecourtsindia.com's public JSON API (paginated, ~836 rows) and
writes them to src/indiacode_acts.json. This is NOT run at request time --
provision_lookup.py fuzzy-matches against this local file so a real
provision lookup costs exactly one outbound HTTP call (the section fetch
itself), not a search call plus a fetch call.

Re-run this occasionally (the corpus grows -- new Acts get passed every
year) but never from the request path. See FINDINGS.md F-24.

Usage:
    python scripts/build_indiacode_acts_index.py
"""

from __future__ import annotations

import json
import os
import time

import requests

API = "https://indiacode.ecourtsindia.com/api/v1/acts"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "indiacode_acts.json")
PAGE = 200


def main() -> None:
    acts = []
    offset = 0
    while True:
        resp = requests.get(API, params={"jurisdiction": "central", "limit": PAGE, "offset": offset},
                            headers={"User-Agent": "Mozilla/5.0 (CaseMap build script; one-time index fetch)"},
                            timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for a in data["acts"]:
            acts.append({"id": a["id"], "short_title": a["short_title"], "act_year": a.get("act_year")})
        print(f"  fetched {len(acts)}/{data['total']}")
        if not data.get("next") or len(data["acts"]) == 0:
            break
        offset += PAGE
        time.sleep(0.2)  # polite pacing, not required by the site but costs nothing

    acts.sort(key=lambda a: a["id"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(acts, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(acts)} acts -> {OUT}")


if __name__ == "__main__":
    main()
