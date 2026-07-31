from typing import TYPE_CHECKING, Protocol

from core.logging import logger

if TYPE_CHECKING:
    # Only for type-checking — the real import stays lazy, inside
    # embed() below (same pattern services/llm/local_provider.py uses
    # for `transformers`). `sentence_transformers` transitively imports
    # `torch`, and simply importing torch — before any model is ever
    # loaded — costs a substantial, unavoidable chunk of RSS on its own.
    # This module used to import it at module scope, meaning every
    # process that merely imported core.embeddings (i.e. every process,
    # since api/dependencies.py imports it at startup) paid that cost
    # immediately, whether or not embedding was ever used. That eager
    # import, stacked with chromadb's (see core/vector_store.py), is
    # what pushed this service's startup memory over Render's limit
    # (exit code 137).
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
    is cheap — it just remembers the model name. Both the
    `sentence_transformers` import itself AND the actual weights (a real
    disk read, and a real network download the very first time this
    model name is ever used on a machine) are deferred to the first call
    to embed(), not import time or construction time.

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
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading SentenceTransformer model '%s' for the first time",
                self._model_name,
            )
            self._model = SentenceTransformer(self._model_name)
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return vectors.tolist()
