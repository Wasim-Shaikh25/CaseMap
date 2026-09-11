# Design: install recipe, not a second NER path

**Date:** 2026-09-10

`load_opennyai_ner()` already does the right thing: `spacy.load("en_legal_ner_sm")`
or raise. Do not add a fallback model. Change the **install instructions** that
`_fail()` prints, and ship `scripts/install_en_legal_ner_sm.py` that:

1. Downloads `en_legal_ner_sm-any-py3-none-any.whl`
2. Saves it as `en_legal_ner_sm-3.2.0-py3-none-any.whl`
3. `pip install` that file
4. Reinstalls `spacy==3.8.16` and the pins in `requirements.txt` so Python 3.11 /
   pydantic v2 still work

`--allow-degraded` stays for development. Default remains raise.
