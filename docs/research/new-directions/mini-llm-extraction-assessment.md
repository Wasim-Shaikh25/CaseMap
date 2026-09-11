# Assessment: small local models for party/date/amount extraction

**Date:** 2026-09-09
**Status:** one-off measurement, not adopted, not wired into `src/` (Part 2 below is
the exception — see its own note on what it confirms about the *existing* mandatory
architecture).
**Why this exists:** before committing more build effort to the deterministic +
OpenNyAI pipeline (`docs/spec/ARCHITECTURE.md`), the owner asked what a small, cheap,
local model would actually produce on real documents — is it worth anything, or does
it confirm why `FORBIDDEN.md` §C bans generative models from the extraction/graph
core. Two models were tried:

1. **Qwen2.5 1.5B** (generic, generative, zero-shot prompted) — Part 1 below.
2. **`en_legal_ner_sm`** (OpenNyAI's own model, legal-domain-trained, extractive
   labelling not generative) — Part 2 below, added after the owner asked for a
   genuinely legal-trained, under-100M model. This is not a new candidate — it is the
   model `docs/spec/ARCHITECTURE.md` §2 already lists as mandatory, and installing and
   running it for real was `HANDOFF.md` §8 item 1 / the top item in
   `CaseMap_AGENT_HANDOFF.md` §7 — unattempted in every session until this one.

## Part 1 — Qwen2.5 1.5B (generic, generative)

## What was tested

- **Model:** `qwen2.5:1.5b` (Ollama, CPU, temperature 0, local — no data left the
  machine). Not a prior CaseMap candidate; see "why not AYN" below.
- **Data:** 20 real Indian court judgments, freshly pulled into `testdata/` for this
  session (source: indiankanoon.org, public-domain judgment text; see
  `testdata/README.md` for provenance and licensing notes) — Supreme Court, five High
  Courts, NCLAT, a State Consumer Commission, and an ITAT bench, covering criminal,
  matrimonial, civil/contract, tax, motor vehicle, land/property, labour, insolvency,
  constitutional, consumer, company, bail/NDPS, rent-control and succession matters.
- **Task:** one-shot prompt asking for strict JSON — court, case number, parties (name
  + role), dates, amounts — from up to 6000 characters of each document. No
  fine-tuning, no few-shot examples, no retries.
- **Script:** `temp/2026-09-09-mini-llm-poc/run_mini_llm_extraction.py`. Raw output:
  `temp/2026-09-09-mini-llm-poc/results.json`.

### Why not AYN (the one legal-specific candidate already on record)

`CaseMap_AGENT_HANDOFF.md` §6 already investigated AYN (88M, Indian-legal,
decoder-only) and logged it as rejected with **no confirmed public checkpoint found**.
That finding was not re-litigated — no checkpoint turned up this time either. Qwen2.5
1.5B was used instead purely because it is a generic, small, instruction-tuned model
Ollama can run zero-shot with no fine-tuning.

## What the check actually measures

For every party name / date / amount the model returned, the script checks whether
that exact string (after whitespace normalization) appears verbatim in the source
document. This is a direct test of the one thing this project cannot compromise on
(`FORBIDDEN.md` §C11, `THESIS.md` §5): **nothing in the extraction core may be
invented — only selected as a verbatim span.**

## Results (20/20 documents, ~21s/doc average on CPU)

| Metric | Result |
|---|---|
| JSON parsed cleanly | 19/20 |
| Party-name verbatim rate (avg) | 95.3% |
| Amount-string verbatim rate (avg, naive string match) | 44.1% |

**The amount number is misleading on its own** — see below, most of the gap is the
model reformatting punctuation (`Rs.15,000` → `Rs. 15,000`, dropping/adding a `/-`
suffix), which a real system would run through the project's own
`normalize_amount()`-style comparator, not a raw string match. Once formatting
differences are excluded, amount *content* was preserved correctly in every case
checked by hand.

## The two failures that matter

1. **Degenerate repetition loop (`13_companies_sc_shanti_prasad_jain_v_kalinga_tubes.txt`).**
   The model got partway through the party list, latched onto "Rath" / "Respondent",
   and repeated that pair over 20 times until output was truncated — never produced
   valid JSON. This is not a hallucination in the BUG-24 sense (inventing a
   confident-but-wrong fact); it is a different, arguably worse failure mode for an
   unattended pipeline: **silent non-termination that has to be caught by a timeout,
   not by a confidence check.** The existing pipeline's rule that "every fallback
   ladder must terminate, never crash" (`docs/spec/ARCHITECTURE.md` §3) has no
   equivalent guarantee from a generative model — this is exactly the kind of
   structural risk that guardrail was written to keep out.

2. **Page-furniture misread as a dollar amount
   (`02_financial_delhihc_amrit_sandhu_v_state.txt`).** The source document's page
   header `$~5` (a routine Delhi HC internal cause-list marker, unrelated to money)
   was returned by the model as an amount, `"$5"`. This is a small-scale version of
   BUG-24: OCR/layout noise being read as a substantive fact instead of being
   recognized as noise.

Also worth noting: the model sometimes folded a full name+address block into a single
`"name"` field (`20_civil_keralahc_kali_ammal_v_valliyammal.txt`) rather than
separating party name from address the way `document_profile.py`'s deterministic
ladder is built to. And it occasionally extracted a narrative description
("French company") as if it were a formal party name — a plausible-sounding but
un-grounded inference the deterministic ladder's role-marker regex wouldn't produce
because it only fires on actual marker text.

## Conclusion

On the narrow question the owner asked — "is it useful, before we build more" — the
honest answer is **mixed, not a clean yes or no**:

- Party-name extraction is *mostly* faithful (95%+ verbatim) even with zero
  fine-tuning, which is better than a skeptic might expect from a 1.5B model.
- But it fails in exactly the two ways `FORBIDDEN.md`/`THESIS.md` already worry about:
  ungrounded inference on noisy input (item 2 above), and — new information from this
  test — **unpredictable non-termination** that a deterministic ladder structurally
  cannot exhibit.
- Neither failure showed up as a confident wrong answer with no warning sign (both
  were either obviously malformed output or an obviously-wrong short string) — but at
  pipeline scale, "obviously wrong to a human reviewer" is not the same guarantee as
  "always confidence-gated by code," which is what G1 in `docs/spec/ARCHITECTURE.md`
  §4 requires.

**This does not change the mandatory-OpenNyAI / no-generative-LLM-in-the-core rule.**
It's evidence, not a proposal to revisit `FORBIDDEN.md` §C — that stays an
owner-reserved decision (`HANDOFF.md` §9). If a generative model is ever considered
again for anything adjacent to the core (e.g., a human-reviewed summarization aid
outside the extraction/graph path), this run is the baseline to compare against, and
the repetition-loop failure mode specifically should be load-bearing in that
decision.

## Part 2 — `en_legal_ner_sm` (OpenNyAI's own mandatory model, extractive)

### Why this replaces the search for a small generative legal model

After Part 1, the owner asked for a genuinely legal-domain-trained model under 100M
params. A fresh Hugging Face survey (2026-09-09) found nothing credible in that space:
AYN (the one candidate `CaseMap_AGENT_HANDOFF.md` §6 already investigated) still has no
public checkpoint anywhere; the one community "under-100M legal" upload found
(`narendraalluri/slm-125m-base`) has zero downloads/likes and no documented training
data or evaluation — not trustworthy for a real comparison; everything else tagged
"legal" + generative on HF is 1B+ or not legal-domain-specific. The one real,
well-documented, small (well under 100M — a token2vec+NER pipeline, no transformer),
legal-trained, CPU-only model that actually exists is `en_legal_ner_sm` — which is not
a new candidate at all, it is OpenNyAI's own model that `opennyai_bridge.py` and
`docs/spec/ARCHITECTURE.md` §2 already require as mandatory, and which no session had
ever actually installed and run until now.

### Getting it running (Windows-specific, for the next session)

This machine has two pre-existing, conflicting spaCy installs (system-wide 3.2.6 with
old `pydantic` 1.x, and a newer 3.8.16 pulled in for this session with `pydantic` 2.x),
and the model wheel's own dependency pin (`spacy<3.3.0,>=3.2.2`) collides with that.
What worked: a dedicated venv
(`temp/2026-09-09-mini-llm-poc/venv_ner/`), `pip install spacy` (latest, 3.8.16),
install the model wheel (renamed locally — the file HuggingFace serves,
`en_legal_ner_sm-any-py3-none-any.whl`, has an invalid PEP 440 version segment `any`
that current `pip` rejects outright; downloading it and renaming to
`en_legal_ner_sm-3.2.0-py3-none-any.whl` fixes that), then re-upgrading `spacy`,
`typer`, `weasel`, `wasabi`, `smart-open` back to versions matching 3.8.16 (installing
the model wheel drags in its own old pins). `spacy.load()` then emits a
compatibility warning (trained on spaCy 3.2.2, running on 3.8.16) but loads and runs
correctly — output matches the model card's documented example exactly.

### Results (20/20 documents, ~0.06s/doc average on CPU)

| Metric | Qwen2.5 1.5B (Part 1) | `en_legal_ner_sm` |
|---|---|---|
| Speed | ~21s/doc | ~0.06s/doc (**~350x faster**) |
| Termination guarantee | No (1/20 hung in a repetition loop) | Yes, always (extractive, not generative) |
| Verbatim guarantee | No (checked empirically, ~95% for names) | **Yes, by construction** — every entity is a source-text span with char offsets, invention is structurally impossible |
| Total entities found (20 docs) | n/a (JSON fields, not spans) | 704, across 14 label types |
| Role-label spans (PETITIONER/RESPONDENT/JUDGE/COURT) | n/a | 222 |
| Obviously mislabeled among those (crude check) | n/a | ~8/222 (3.6%) |

Label breakdown across all 20 documents: DATE 111, OTHER_PERSON 109, PETITIONER 68,
RESPONDENT 59, COURT 52, STATUTE 52, PROVISION 52, CASE_NUMBER 47, LAWYER 44, JUDGE 43,
ORG 26, GPE 25, PRECEDENT 11, WITNESS 5.

### What the errors actually look like

Because every entity is a verbatim span, this model cannot invent a party name the way
a generative model can — its failures are a different, narrower class: **right text,
wrong label**, or a stray irrelevant span, never fabricated content. Examples pulled
directly from the run:

- **Real wins:** on the 17-respondent consumer case
  (`12_consumer_stateconsumercommission_prudential_v_kukreja.txt`), it correctly
  labelled essentially all 17 named respondents as `RESPONDENT` — a harder case than
  anything Qwen was asked to handle at that scale, and one the deterministic regex
  ladder alone was not built to guarantee either.
- **Role confusion:** in `01_criminal_sc_dilip_kumar_sharma_v_mp.txt`, the same person
  (`Dilip Kumar`) is tagged `PETITIONER` in some mentions and `RESPONDENT` in others
  within the same document — the model's PETITIONER/RESPONDENT labels track *local*
  sentence context, not a stable per-document role assignment.
- **Role/entity-type mix-ups:** a lawyer's name (`A. N. Mulla`,
  `01_criminal_...`) labelled `PETITIONER` instead of `LAWYER`; another lawyer's name
  (`K.K. Mishra`, `09_insolvency_...`) labelled `JUDGE`; a statute abbreviation
  (`SICA`, `12_consumer_...`) labelled `COURT`.
- **Metadata mistaken for a party:** header lines like `"Author: Ashok Bhushan"` or
  a full case title (`"Rajnesh vs Neha"`) occasionally get labelled `PETITIONER`
  wholesale.

**This is not a new problem for the project — it is exactly why the mandatory
architecture is two layers, not one.** `docs/spec/ARCHITECTURE.md` §1 stage [2] already
specifies: "Layer 1 (mandatory): OpenNyAI ML NER — party NAMES + rough side. Layer 2
(mandatory): deterministic CASE_TYPE_ROLES — precise role refinement... this layer
always runs on ML output, never skipped." This run is the first real evidence, on real
documents, of *why* that second layer has to run on every output rather than trusting
Layer 1's PETITIONER/RESPONDENT label directly — the raw label alone gets roughly 1 in
25-30 role-tagged spans wrong or noisy.

### Conclusion for Part 2

Unlike Part 1, this is not "evidence against adopting X" — it's the first real
confirmation that the architecture already committed to (mandatory two-layer party
extraction) is built the way it needs to be. Concretely:

- The speed and termination guarantees make this categorically safer to run
  unattended than any generative model, at any size.
- The verbatim-by-construction guarantee means it cannot violate `FORBIDDEN.md` §C in
  the way a generative model structurally can.
- Its label noise (role confusion, entity-type mix-ups, occasional metadata spans) is
  real, present in every document type tested, and is exactly what Layer 2's
  deterministic `CASE_TYPE_ROLES` refinement exists to catch — reinforcing, not
  undermining, `docs/spec/ARCHITECTURE.md` §4 guardrail G2's requirement that this stay
  the sole mandatory ML entry point in the core.

**This closes `HANDOFF.md` §8 item 1 / the top item in `CaseMap_AGENT_HANDOFF.md` §7**
— the model has now actually been installed and run against real documents, for the
first time in this project's history. The venv and install recipe above are the
starting point for wiring this into `opennyai_bridge.py` for real (removing
`--allow-degraded` as the default), which remains separate, larger work — not done in
this session.

## Where things are, for the next session

- `testdata/` — the 20 real documents (kept for reuse in future POC/testing work).
- `temp/2026-09-09-mini-llm-poc/` — both scripts (`run_mini_llm_extraction.py`,
  `run_en_legal_ner_sm.py`), raw JSON results for both runs, the wheel file, and the
  working `venv_ner/` virtualenv with `en_legal_ner_sm` actually installed and
  confirmed loadable (ephemeral, per `AGENTS.md` §9's routing table — safe to delete
  once this write-up is trusted, but the venv in particular is worth keeping a bit
  longer since reproducing the Windows dependency fix took real effort; see the recipe
  above before deleting it).
