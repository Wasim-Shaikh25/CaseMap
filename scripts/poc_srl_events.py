"""
poc_srl_events.py -- measures whether casemap_pipeline.detect_events_srl()
(the WHO/ACTION/WHAT/WHEN dependency-parse layer, F-16) still finds anything
the REAL live pipeline (casemap_service.process_document() -- the exact code
path server/app.py and poc_run.py both use, SRL layer included) doesn't
already surface.

History: the first version of this script compared only against
casemap_pipeline.detect_events() (the fixed EVENT_KEYWORDS phrase scanner)
in isolation and found a 73% miss rate. That overstated the real gap --
casemap_service.py already had a second coverage layer,
_events_for_uncovered_dates() (DATED_EVENT nodes), plus important_lines.py's
per-paragraph central-sentence pick. Re-measured against the FULL real
output (this script), the true gap before detect_events_srl() existed was
23% (scripts stayed in git history / CHANGELOG for the exact numbers). After
wiring detect_events_srl() into casemap_service.py, re-running this script
should show ~0% left -- if it doesn't, that's a real bug to chase, not
rounding.

Match rule: a real event "covers" an SRL-flagged sentence if the sentence's
own text is a normalized substring of that event's display text, or vice
versa (real events are sentence/snippet-bounded already, per
_line_bounds()/_sat_sentence_spans()/_sentence_bounds() -- see
casemap_service.py).

Usage:
    python poc_srl_events.py ../testdata/01_criminal_sc_dilip_kumar_sharma_v_mp.txt
    python poc_srl_events.py ../testdata/*.txt --max-samples 6
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import spacy  # noqa: E402
import casemap_service as service  # noqa: E402
from casemap_pipeline import EVENT_KEYWORDS  # noqa: E402

SUBJ_DEPS = {"nsubj", "nsubjpass"}
OBJ_DEPS = {"dobj", "attr", "oprd", "dative"}
_WS_RE = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS_RE.sub(" ", s).strip().lower()


def matches_existing_keywords(sent_text_lower: str) -> bool:
    for kws in EVENT_KEYWORDS.values():
        for kw in kws:
            if kw in sent_text_lower:
                return True
    return False


def find_root_verb(sent):
    for tok in sent:
        if tok.dep_ == "ROOT" and tok.pos_ in ("VERB", "AUX"):
            return tok
    return sent.root


def describe_sentence(sent, dates, modals) -> dict | None:
    root = find_root_verb(sent)
    who = [tok.text for tok in root.children if tok.dep_ in SUBJ_DEPS]
    what_objs = [tok.text for tok in root.children if tok.dep_ in OBJ_DEPS]
    for child in root.children:
        if child.dep_ == "prep":
            what_objs += [gc.text for gc in child.children if gc.dep_ == "pobj"]
    if not who and not what_objs:
        return None
    return {
        "who": who,
        "action": root.lemma_ if root.pos_ in ("VERB", "AUX") else None,
        "what": what_objs,
        "when": [d.text for d in dates],
        "modal": [m.text for m in modals],
        "text": sent.text.strip(),
    }


def real_event_texts(path: str) -> list[str]:
    """Run the ACTUAL product pipeline and collect every text span it
    already surfaced, across ALL of its layers (keyword events, important
    lines, DATED_EVENT fallback, section fallback)."""
    name = os.path.basename(path)
    result = service.process_document(path, name, ml_nlp=None)
    texts = []
    for e in result.get("events", []):
        texts.append(norm(e.get("section_text") or ""))
        for src in e.get("sources", []):
            if src.get("text"):
                texts.append(norm(src["text"]))
    return [t for t in texts if t]


def is_covered(sent_norm: str, real_texts: list[str]) -> bool:
    if not sent_norm:
        return True
    for t in real_texts:
        if sent_norm in t or t in sent_norm:
            return True
    return False


def analyze_document(nlp, path: str, max_samples: int) -> dict:
    text = open(path, encoding="utf-8", errors="replace").read()
    doc = nlp(text[:900_000])
    real_texts = real_event_texts(path)

    total_sents = event_like = already_real = new_srl = 0
    samples = []

    for sent in doc.sents:
        total_sents += 1
        dates = [e for e in sent.ents if e.label_ == "DATE"]
        modals = [t for t in sent if t.tag_ == "MD"]
        if not dates and not modals:
            continue
        event_like += 1

        sent_norm = norm(sent.text)
        if is_covered(sent_norm, real_texts):
            already_real += 1
            continue

        info = describe_sentence(sent, dates, modals)
        if info is None:
            continue
        new_srl += 1
        if len(samples) < max_samples:
            samples.append(info)

    return {
        "path": path, "total_sents": total_sents, "event_like": event_like,
        "already_real": already_real, "new_srl": new_srl, "samples": samples,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--max-samples", type=int, default=5)
    args = ap.parse_args()

    paths = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        paths.extend(matched if matched else [pattern])
    paths = sorted(set(paths))

    print("[+] loading en_core_web_sm ...")
    nlp = spacy.load("en_core_web_sm")

    g_total = g_event_like = g_already = g_new = 0

    for path in paths:
        if not os.path.isfile(path):
            print(f"[!] skip (not found): {path}")
            continue
        print(f"[+] running full real pipeline + SRL scan on {os.path.basename(path)} ...")
        r = analyze_document(nlp, path, args.max_samples)
        g_total += r["total_sents"]; g_event_like += r["event_like"]
        g_already += r["already_real"]; g_new += r["new_srl"]

        print(f"\n=== {os.path.basename(path)} ===")
        print(f"  sentences total:                    {r['total_sents']}")
        print(f"  event-like (date or modal):         {r['event_like']}")
        print(f"  already surfaced by REAL pipeline:  {r['already_real']}")
        print(f"  genuinely NEW (SRL only):            {r['new_srl']}")
        for i, s in enumerate(r["samples"], 1):
            print(f"    [{i}] WHO={s['who']!r} ACTION={s['action']!r} WHAT={s['what']!r} "
                  f"WHEN={s['when']!r} MODAL={s['modal']!r}")
            print(f"        \"{s['text'][:160]}\"")

    print("\n=== TOTAL ===")
    print(f"  event-like sentences:               {g_event_like}")
    print(f"  already surfaced by real pipeline:  {g_already}")
    print(f"  genuinely NEW (SRL only):            {g_new}"
          f"  ({g_new / max(g_event_like, 1):.0%} of event-like sentences)")


if __name__ == "__main__":
    main()
