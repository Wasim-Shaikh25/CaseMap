"""
tune_rhetorical_embedding.py -- sanity-check + threshold tuning for
rhetorical_roles.match_cue_embedding() (F-19): the embedding fallback that
catches a Facts/Issues/Arguments/Ruling paragraph phrased differently than
RHETORICAL_ROLE_CUES' own fixed phrases.

Not a permanent test -- a one-off tuning aid, same spirit as
scripts/poc_srl_events.py. Run against real testdata/*.txt to see how many
additional paragraphs the embedding layer tags (embedding_matched) beyond
what the exact/fuzzy phrase match already catches (cue_matched), and spot-
check a sample for correctness before trusting the chosen threshold/margin.

Usage:
    python tune_rhetorical_embedding.py ../testdata/*.txt
"""

from __future__ import annotations

import glob
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from rhetorical_roles import tag_document  # noqa: E402


def main():
    paths = []
    for pattern in sys.argv[1:]:
        matched = glob.glob(pattern)
        paths.extend(matched if matched else [pattern])
    paths = sorted(set(paths))

    grand = Counter()
    samples = []

    for path in paths:
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        tagged = tag_document(text)
        counts = Counter(t["confidence"] for t in tagged)
        grand.update(counts)
        print(f"{os.path.basename(path):55s} {dict(counts)}")
        for t in tagged:
            if t["confidence"] == "embedding_matched" and len(samples) < 25:
                samples.append((os.path.basename(path), t["role"], t["text"][:140].replace("\n", " ")))

    print("\n=== TOTAL ===")
    print(dict(grand))
    print(f"\n=== embedding_matched samples (spot-check these for correctness) ===")
    for doc, role, text in samples:
        print(f"[{role:24s}] {doc}: \"{text}\"")


if __name__ == "__main__":
    main()
