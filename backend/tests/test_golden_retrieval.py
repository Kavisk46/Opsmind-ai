"""A small golden evaluation set for retrieval — the mechanism that
catches a REGRESSION in retrieval quality (a chunking change, a
similarity-scoring change, a RetrievalService refactor) that every other
test in this suite structurally cannot: every other retrieval-adjacent
test (test_retrieval_service.py, test_vector_store.py) uses fakes with
CONTROLLED, arbitrary results — they prove the plumbing works, never
whether a REALISTIC query actually finds the RIGHT document among several
plausible ones. That's what this file is for.

Why not conftest.py's FakeEmbeddingModel: it's length-based
(`len(text) % 7`) — completely uncorrelated with meaning, by design, since
every test that uses it only needs distinct-but-arbitrary vectors (see
its docstring). A golden regression set built on top of it would be
worthless: it couldn't tell a question about billing apart from one about
outages. GoldenFakeEmbeddingModel below is a SECOND, different kind of
fake — still deterministic and network-free (same rules as every other
fake in this suite), but built to actually encode topical similarity via
simple keyword-occurrence counts over a small fixed vocabulary. It is
intentionally crude (this isn't a real embedding model, and never claims
to be) — just precise enough that "a question about X" reliably scores
highest against "a document about X," which is all a regression check
needs.
"""

import shutil
import tempfile
import uuid

import pytest

from core.vector_store import VectorStore
from services.retrieval_service import RetrievalService

_GOLDEN_VOCAB = ["deploy", "database", "auth", "billing", "outage"]


class GoldenFakeEmbeddingModel:
    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append([float(lowered.count(keyword)) for keyword in _GOLDEN_VOCAB])
        return vectors


# The golden CORPUS — small, representative documents, each written to
# clearly belong to one topic in _GOLDEN_VOCAB. "id" is a short, stable,
# human-readable label (not a real UUID) used only to cross-reference
# against GOLDEN_QUERIES below.
GOLDEN_DOCUMENTS = [
    {
        "id": "deploy-runbook",
        "text": "The deployment pipeline failed during canary rollout and had to be rolled back manually.",
    },
    {
        "id": "database-migration",
        "text": "We migrated the primary database schema without any downtime last Tuesday.",
    },
    {
        "id": "auth-incident",
        "text": "Multiple users could not log in after the authentication service update; auth tokens were rejected.",
    },
    {
        "id": "billing-bug",
        "text": "A duplicate webhook caused the billing system to charge some customers twice this month.",
    },
    {
        "id": "outage-postmortem",
        "text": "A full service outage occurred when database connections were exhausted under heavy load.",
    },
]

# The golden QUERY set — realistic questions a user might actually ask,
# each paired with the ONE document it should retrieve. Every query below
# uses a keyword unique enough (relative to _GOLDEN_VOCAB) to have exactly
# one clear best match — a deliberate corpus-design choice, not an
# accident (see this phase's write-up on why ambiguous golden cases are
# worse than useless: a flaky regression test teaches engineers to ignore
# it).
GOLDEN_QUERIES = [
    {"query": "How do I roll back a failed deployment?", "expected_document_id": "deploy-runbook"},
    {"query": "What happened during the database migration?", "expected_document_id": "database-migration"},
    {"query": "Why is auth rejecting valid users?", "expected_document_id": "auth-incident"},
    {"query": "Why does billing show duplicate charges?", "expected_document_id": "billing-bug"},
    {"query": "What caused the outage?", "expected_document_id": "outage-postmortem"},
]


def test_every_golden_query_contains_at_least_one_vocabulary_keyword():
    # A real bug this file's first draft hit directly: "Why couldn't
    # users log in?" contains none of _GOLDEN_VOCAB's literal words, so
    # GoldenFakeEmbeddingModel embedded it as an all-zero vector —
    # undefined similarity against everything, so Chroma's tie-breaking
    # (not real matching) decided the result. This test guards against
    # that exact mistake recurring silently as the golden set grows —
    # a query with an all-zero embedding would otherwise still "pass or
    # fail" the parametrized test above for the wrong reason.
    for case in GOLDEN_QUERIES:
        lowered_query = case["query"].lower()
        assert any(keyword in lowered_query for keyword in _GOLDEN_VOCAB), (
            f"query {case['query']!r} contains no _GOLDEN_VOCAB keyword — "
            "its embedding would be an all-zero vector"
        )


@pytest.fixture()
def golden_index():
    """Seeds a REAL, temp-dir VectorStore with the golden corpus, embedded
    via GoldenFakeEmbeddingModel — deliberately real VectorStore + real
    RetrievalService, with only the embedding model faked, so this
    exercises the actual retrieval code path end-to-end, not a mocked
    approximation of it.
    """
    persist_dir = tempfile.mkdtemp()
    vector_store = VectorStore(persist_dir)
    embedding_model = GoldenFakeEmbeddingModel()
    owner_id = uuid.uuid4()

    document_ids: dict[str, str] = {}
    for doc in GOLDEN_DOCUMENTS:
        document_id = str(uuid.uuid4())
        document_ids[doc["id"]] = document_id
        embedding = embedding_model.embed([doc["text"]])
        vector_store.add_chunks(
            document_id=document_id, owner_id=str(owner_id),
            chunks=[doc["text"]], embeddings=embedding,
        )

    service = RetrievalService(embedding_model=embedding_model, vector_store=vector_store)
    yield service, document_ids, owner_id
    shutil.rmtree(persist_dir, ignore_errors=True)


@pytest.mark.parametrize(
    "case", GOLDEN_QUERIES, ids=[c["expected_document_id"] for c in GOLDEN_QUERIES]
)
def test_golden_query_retrieves_the_expected_document(golden_index, case):
    service, document_ids, owner_id = golden_index

    results = service.retrieve(query=case["query"], owner_id=owner_id, top_k=1)

    assert len(results) == 1
    assert str(results[0].document_id) == document_ids[case["expected_document_id"]]


def test_golden_query_for_deploy_topic_does_not_match_unrelated_billing_document(golden_index):
    # A negative case, not just positive ones — proving retrieval
    # correctly DISCRIMINATES between topics, not just that it returns
    # *something* plausible-looking for every query.
    service, document_ids, owner_id = golden_index

    results = service.retrieve(
        query="How do I roll back a failed deployment?", owner_id=owner_id, top_k=1
    )

    assert str(results[0].document_id) != document_ids["billing-bug"]
