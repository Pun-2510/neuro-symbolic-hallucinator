"""Regression tests for local-database-first retrieval."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from integrity_checker.database import LocalDatabase, Paper
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator


def _client(name: str, result: SourceCandidate | None = None) -> object:
    client = type("StubClient", (), {})()
    client.name = name
    client.lookup = AsyncMock()
    if result is None:
        client.lookup.side_effect = AssertionError(
            f"External API {name!r} was called after the paper was cached"
        )
    else:
        client.lookup.return_value = result
    return client


@pytest.mark.asyncio
async def test_api_result_is_synced_then_reused_from_local_db(tmp_path) -> None:
    """A second retrieval of an API result must be a DB hit, not an API call."""
    db = LocalDatabase(tmp_path / "local_papers.db")
    citation = Citation(
        raw_text="New API Paper",
        title="New API Paper",
        authors=["Roe, John"],
        year="2021",
    )
    api_candidate = SourceCandidate(
        source_name="crossref",
        found=True,
        doi="10.5555/new-api-paper",
        title="New API Paper",
        authors=["Roe, John"],
        year="2021",
        confidence=0.9,
    )

    first_clients = [
        _client("crossref", api_candidate),
        _client("openalex", SourceCandidate(source_name="openalex", found=False, error="not found")),
        _client(
            "semantic_scholar",
            SourceCandidate(source_name="semantic_scholar", found=False, error="not found"),
        ),
        _client("arxiv", SourceCandidate(source_name="arxiv", found=False, error="not used")),
    ]
    first = RetrievalOrchestrator(
        crossref=first_clients[0],
        openalex=first_clients[1],
        semantic_scholar=first_clients[2],
        arxiv=first_clients[3],
        local_db=db,
        use_local_db=True,
        parallel=True,
    )
    first_result = await first.retrieve(citation)

    assert first_result.sources_succeeded == ["crossref"]
    assert db.find_by_doi("https://doi.org/10.5555/new-api-paper") is not None
    assert first_clients[0].lookup.await_count == 1

    second_clients = [_client(name) for name in ("crossref", "openalex", "semantic_scholar", "arxiv")]
    second = RetrievalOrchestrator(
        crossref=second_clients[0],
        openalex=second_clients[1],
        semantic_scholar=second_clients[2],
        arxiv=second_clients[3],
        local_db=db,
        use_local_db=True,
        parallel=True,
    )
    second_result = await second.retrieve(
        Citation(
            raw_text="https://doi.org/10.5555/new-api-paper",
            doi="https://doi.org/10.5555/new-api-paper",
        )
    )

    assert second_result.sources_succeeded == ["local_db"]
    assert second_result.best_candidate() is not None
    assert second_result.best_candidate().paper_id is not None
    assert all(client.lookup.await_count == 0 for client in second_clients)


@pytest.mark.asyncio
async def test_existing_doi_in_local_db_skips_all_external_clients(tmp_path) -> None:
    """A known DOI is resolved locally before any API client is touched."""
    db = LocalDatabase(tmp_path / "local_papers.db")
    paper_id = db.add_paper(
        Paper(
            doi="10.1234/verified-paper.",
            title="A Verified Local Paper",
            authors=["Doe, Jane"],
            year=2020,
            venue="Test Journal",
        )
    )

    clients = [_client(name) for name in ("crossref", "openalex", "semantic_scholar", "arxiv")]
    orchestrator = RetrievalOrchestrator(
        crossref=clients[0],
        openalex=clients[1],
        semantic_scholar=clients[2],
        arxiv=clients[3],
        local_db=db,
        use_local_db=True,
        parallel=True,
    )
    result = await orchestrator.retrieve(
        Citation(
            raw_text="10.1234/verified-paper",
            doi="https://doi.org/10.1234/verified-paper",
        )
    )

    assert result.sources_succeeded == ["local_db"]
    assert result.best_candidate() is not None
    assert result.best_candidate().paper_id == paper_id
    assert all(client.lookup.await_count == 0 for client in clients)
