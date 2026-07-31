import io


def _auth_headers(client, email: str = "retrieval-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Retrieval User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_document(client, headers: dict, filename: str, content: bytes) -> str:
    upload = client.post(
        "/documents",
        headers=headers,
        files={"file": (filename, io.BytesIO(content), "text/plain")},
    )
    # TestClient runs BackgroundTasks synchronously, so ingestion (including
    # the new Postgres chunk mirror) has already completed by the time this
    # returns — no polling needed, same as every other ingestion-dependent
    # test in this suite.
    return upload.json()["id"]


def test_search_without_auth_returns_401(client):
    response = client.post("/retrieval/search", json={"question": "what happened?"})
    assert response.status_code == 401


def test_search_with_empty_question_returns_400(client):
    headers = _auth_headers(client)
    response = client.post("/retrieval/search", headers=headers, json={"question": "   "})
    assert response.status_code == 400


def test_search_returns_context_citations_and_chunks_for_a_matching_document(client):
    headers = _auth_headers(client, email="retrieval-happy@example.com")
    _upload_document(
        client, headers, filename="bottlenecks.txt",
        content=b"OpsMind helps teams find operational bottlenecks.",
    )

    response = client.post(
        "/retrieval/search", headers=headers, json={"question": "operational bottlenecks"}
    )

    assert response.status_code == 200
    body = response.json()
    assert "bottlenecks" in body["context"].lower()
    assert len(body["citations"]) > 0
    assert body["citations"][0]["filename"] == "bottlenecks.txt"
    assert len(body["chunks"]) > 0
    assert body["chunks"][0]["combined_score"] is not None


def test_search_never_returns_another_owners_chunks(client):
    owner_a_headers = _auth_headers(client, email="retrieval-owner-a@example.com")
    owner_b_headers = _auth_headers(client, email="retrieval-owner-b@example.com")
    _upload_document(
        client, owner_a_headers, filename="secret-plan.txt",
        content=b"The confidential quarterly roadmap details.",
    )

    response = client.post(
        "/retrieval/search",
        headers=owner_b_headers,
        json={"question": "quarterly roadmap"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chunks"] == []
    assert body["citations"] == []


def test_search_returns_empty_results_for_a_user_with_no_documents(client):
    headers = _auth_headers(client, email="retrieval-empty@example.com")

    response = client.post(
        "/retrieval/search", headers=headers, json={"question": "anything at all"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chunks"] == []
    assert body["citations"] == []
    assert "No relevant context" in body["context"]


def test_search_matches_via_filename_keyword_even_without_content_overlap(client):
    headers = _auth_headers(client, email="retrieval-filename@example.com")
    _upload_document(
        client, headers, filename="q3-budget-report.txt",
        content=b"Numbers and figures for the period under review.",
    )

    response = client.post(
        "/retrieval/search", headers=headers, json={"question": "budget"}
    )

    assert response.status_code == 200
    body = response.json()
    assert any(chunk["filename"] == "q3-budget-report.txt" for chunk in body["chunks"])


def test_search_calls_no_llm(client):
    # The whole point of this phase's stop condition — proves the fake
    # LLM this fixture wires up for chat is never touched by this route.
    headers = _auth_headers(client, email="retrieval-no-llm@example.com")
    _upload_document(client, headers, filename="notes.txt", content=b"some content here")

    client.post("/retrieval/search", headers=headers, json={"question": "some content"})

    assert client.fake_llm.last_prompt is None


def test_search_handles_a_large_query_without_error(client):
    headers = _auth_headers(client, email="retrieval-large-query@example.com")
    _upload_document(client, headers, filename="notes.txt", content=b"some content here")
    large_question = "word " * 2000

    response = client.post(
        "/retrieval/search", headers=headers, json={"question": large_question}
    )

    assert response.status_code == 200


def test_search_respects_a_client_supplied_top_k(client):
    headers = _auth_headers(client, email="retrieval-top-k@example.com")
    # Long enough to produce multiple chunks.
    _upload_document(client, headers, filename="notes.txt", content=b"a" * 5000)

    response = client.post(
        "/retrieval/search",
        headers=headers,
        json={"question": "a", "top_k": 1},
    )

    assert response.status_code == 200
