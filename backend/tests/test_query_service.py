import pytest

from services.query_service import EmptyQueryError, ProcessedQuery, QueryService


@pytest.fixture()
def service() -> QueryService:
    return QueryService()


def test_process_trims_leading_and_trailing_whitespace(service):
    result = service.process("   what happened last week?   ")
    assert result.text == "what happened last week?"


def test_process_collapses_internal_whitespace_runs(service):
    result = service.process("what   happened\n\nlast\tweek?")
    assert result.text == "what happened last week?"


def test_process_returns_a_processed_query(service):
    result = service.process("hello")
    assert isinstance(result, ProcessedQuery)


def test_process_estimates_token_count(service):
    result = service.process("one two three four")
    assert result.estimated_token_count == 4


@pytest.mark.parametrize("raw_query", ["", "   ", "\n\t  \n"])
def test_process_rejects_empty_or_whitespace_only_queries(service, raw_query):
    with pytest.raises(EmptyQueryError):
        service.process(raw_query)


def test_process_handles_a_very_large_query_without_error(service):
    large_query = "word " * 5000
    result = service.process(large_query)
    assert result.estimated_token_count == 5000
    assert result.text == " ".join(["word"] * 5000)
