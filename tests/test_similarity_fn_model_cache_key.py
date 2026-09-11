"""F-10: make_similarity_fn()'s model and embedding cache used to be single
shared globals keyed only by text, not by model_name -- a second call with a
different model_name inside the same process silently reused the first
model's loaded weights and cached embeddings. Confirmed by a real POC run:
a second "Qwen" similarity call returned bit-identical scores to a prior
MiniLM call in 0.0s (no load, all cache hits)."""

import casemap_pipeline as cp


def test_different_model_names_get_independent_model_instances():
    cp._EMBED_MODELS.clear()
    cp._EMBED_CACHE.clear()

    class FakeModel:
        def __init__(self, name):
            self.name = name

        def encode(self, txt, normalize_embeddings=True):
            # deterministic, model-specific "embedding" so we can prove which
            # model actually produced a given cached value
            import numpy as np
            return np.array([hash((self.name, txt)) % 1000])

    import sentence_transformers
    orig = sentence_transformers.SentenceTransformer
    sentence_transformers.SentenceTransformer = FakeModel
    try:
        fn_a = cp.make_similarity_fn("model-a")
        fn_b = cp.make_similarity_fn("model-b")

        e1 = {"section_text": "same text for both models"}
        e2 = {"section_text": "same text for both models"}

        fn_a(e1, e2)  # populates the cache for model-a
        assert ("model-a", "same text for both models") in cp._EMBED_CACHE
        assert ("model-b", "same text for both models") not in cp._EMBED_CACHE

        fn_b(e1, e2)  # must NOT reuse model-a's cached embedding
        assert ("model-b", "same text for both models") in cp._EMBED_CACHE
        assert cp._EMBED_CACHE[("model-a", "same text for both models")] is not \
            cp._EMBED_CACHE[("model-b", "same text for both models")]

        assert "model-a" in cp._EMBED_MODELS
        assert "model-b" in cp._EMBED_MODELS
        assert cp._EMBED_MODELS["model-a"] is not cp._EMBED_MODELS["model-b"]
    finally:
        sentence_transformers.SentenceTransformer = orig
        cp._EMBED_MODELS.clear()
        cp._EMBED_CACHE.clear()
