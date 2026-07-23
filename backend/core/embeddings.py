from typing import Protocol

from sentence_transformers import SentenceTransformer


class EmbeddingModel(Protocol):
    """The shape any embedding backend must provide — same Protocol-based
    pattern as core/storage.py's Storage. Lets tests substitute a fake,
    instant, network-free implementation without touching the ingestion
    pipeline that calls it.
    """

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbeddingModel:
    """A local HuggingFace model, loaded lazily. Constructing this object
    is cheap — it just remembers the model name. The actual weights (a
    real disk read, and a real network download the very first time this
    model name is ever used on a machine) only load on the first call to
    embed(), not at import time.

    This is a deliberate trade-off, not an oversight: eager loading at
    startup gives consistent, predictable request latency at the cost of
    slow startup; lazy loading keeps startup (and, importantly, the test
    suite — see tests/conftest.py's FakeEmbeddingModel) fast, at the cost
    of the first real embedding call being slow (a "cold start").
    """

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return vectors.tolist()
