from core.embeddings import SentenceTransformerEmbeddingModel

# No test here ever calls .embed() — doing so would trigger a REAL
# download of model weights the first time this model name is used on a
# machine (see SentenceTransformerEmbeddingModel's docstring), which is
# exactly what this phase's rules forbid ("never download models during
# tests"). What CAN be tested without that: the lazy-loading CONTRACT
# itself — that constructing this object is cheap and touches no model
# at all, which is the property every other fixture/fake in this suite
# (FakeEmbeddingModel) depends on being true in order to keep the whole
# test suite fast and network-free.


def test_construction_does_not_load_a_model():
    model = SentenceTransformerEmbeddingModel("sentence-transformers/all-MiniLM-L6-v2")
    # Private attribute, not a public contract — but there's no public
    # is_loaded-style property here the way LLMProvider has one (see
    # this phase's write-up: a real, minor asymmetry between the two
    # Protocols worth flagging, not silently added to production code
    # as a side effect of writing a test for it).
    assert model._model is None


def test_construction_stores_model_name_without_touching_the_network():
    # Merely constructing this object must be safe to do at import time
    # / app startup (see api/dependencies.py's _embedding_model
    # singleton) — if __init__ itself reached out to HuggingFace Hub,
    # every test run and every app startup would require network access.
    model = SentenceTransformerEmbeddingModel("not-a-real-model-name")
    assert model._model_name == "not-a-real-model-name"
    assert model._model is None
