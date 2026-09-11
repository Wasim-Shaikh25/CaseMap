# CaseMap

A source-grounded, LLM-free-in-the-core visual case-file map for legal document
bundles — every extracted fact traces to a verbatim source span with page/char
provenance, and nothing is invented.

## The laws (read these first)

See `THESIS.md` and `HEART.md` for the full statement. In short:

1. No LLM (generative model) may ever generate, paraphrase, or infer party names,
   dates, amounts, provisions, events, or graph edges in the extraction/graph core —
   only select verbatim spans that validate against source text with char offsets.
2. OpenNyAI's Legal NER is a mandatory extraction/labelling layer, not an optional
   fallback tier.
3. Real documents (`real_docs/`, `real_pdfs/`) are the only valid test oracle. A
   confidently-wrong result is a worse failure than an honest "don't know."

## Documents

- `THESIS.md` — the laws · `HEART.md` — what we want + build tiers
- `docs/spec/SCOPE.md` — the boundary · `docs/spec/ARCHITECTURE.md` — the build spec
- `FORBIDDEN.md` — the mistakes we never repeat · `AGENTS.md` — binding rules
- `STATUS.md` — current state · `CHANGELOG.md` — history · `FINDINGS.md` — the register
- `docs/research/existing-approach/CaseMap_AGENT_HANDOFF.md` — the deep pre-governance technical handoff (architecture,
  full 26-bug ledger, real-document dry-run results, open gaps) — still authoritative
  for implementation detail
- `docs/research/existing-approach/CaseMap_Mandatory_ML_Layer_v7.md` — the mandatory OpenNyAI NER layer, in depth
- `docs/research/existing-approach/poc_report.md` — the most recent POC run's output

## Status

Working local app on top of the extraction/graph pipeline — see `STATUS.md` and
`HANDOFF.md`. A FastAPI backend (`server/app.py`) wraps the `src/` pipeline and a
plain HTML/CSS/JS frontend (`ui/`) provides upload → timeline / documents-insight /
provisions / parties / conflicts, an evidence drawer with page/paragraph/verbatim
context, and a downloadable counsel report. Run it:

```
.venv\Scripts\python.exe -m uvicorn server.app:app --port 8756
```

then open http://127.0.0.1:8756. The earlier "do not build UI" rule (`HANDOFF.md` §0)
was reversed by direct owner instruction (CHANGELOG 42). `scripts/poc_run.py` remains
the original CLI path but has drifted behind the web pipeline. Still not a *hosted*
product — everything runs locally; the browser (`localStorage`) is the only store.

## Default interpreter (mandatory NER)

Project-root `.venv` (Python 3.11) is the default. System Python is known-broken
for this stack. After clone:

```
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\install_en_legal_ner_sm.py
.venv\Scripts\python.exe -m spacy download en_core_web_sm
```

`en_legal_ner_sm` cannot go in `requirements.txt` (invalid PEP 440 wheel). Real
pipeline runs must **not** pass `--allow-degraded`.

```
.venv\Scripts\python.exe scripts\poc_run.py testdata
```

## Picking this up

`HANDOFF.md` is the orientation document: where the project stands, open findings, the
work queue, known traps, and what's reserved for the project owner. Read `FORBIDDEN.md`
and `AGENTS.md` first — those are binding; the handoff is the map.
