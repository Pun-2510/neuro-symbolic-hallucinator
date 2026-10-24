"""Unit tests cho 4 scholarly/book API clients mới:
- DBLPClient (dblp.org)
- ArxivClient (export.arxiv.org)
- OpenLibraryClient (openlibrary.org + Google Books fallback)
- EuropePMCClient (ebi.ac.uk/europepmc)
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from integrity_checker.models.citation import Citation
from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.retrieval.dblp_client import DBLPClient
from integrity_checker.retrieval.europepmc_client import EuropePMCClient
from integrity_checker.retrieval.openlibrary_client import OpenLibraryClient


def _patch_httpx(handler):
    async def mock_get(self, url, **kwargs):
        headers = kwargs.get("headers") or {}
        params = kwargs.get("params") or {}
        req = httpx.Request("GET", url, headers=headers, params=params)
        return handler(req)

    return patch.object(httpx.AsyncClient, "get", mock_get)


# ============================================================
# 1. DBLPClient Tests
# ============================================================


class TestDBLPClient:
    @pytest.fixture
    def client(self):
        return DBLPClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_dblp_lookup_conference_paper_success(self, client):
        """DBLP resolves CS conference paper, strips trailing period and 4-digit author disambiguation."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/search/publ/api" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "result": {
                        "hits": {
                            "hit": [
                                {
                                    "info": {
                                        "title": "Deep Residual Learning for Image Recognition.",
                                        "authors": {
                                            "author": [
                                                {"text": "Kaiming He"},
                                                {"text": "Xiangyu Zhang 0001"},
                                                {"text": "Shaoqing Ren"},
                                                {"text": "Jian Sun 0001"},
                                            ]
                                        },
                                        "venue": "CVPR",
                                        "year": "2016",
                                        "doi": "10.1109/CVPR.2016.90",
                                        "ee": "https://doi.org/10.1109/CVPR.2016.90",
                                        "key": "conf/cvpr/HeZRS16",
                                    }
                                }
                            ]
                        }
                    }
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="He et al. (2016). Deep Residual Learning for Image Recognition. CVPR.",
                title="Deep Residual Learning for Image Recognition",
                authors=["Kaiming He"],
                year="2016",
            )
            res = await client.lookup(cit)

        assert res.found is True
        assert res.source_name == "dblp"
        assert res.title == "Deep Residual Learning for Image Recognition"
        assert res.authors == ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"]
        assert res.year == "2016"
        assert res.venue == "CVPR"
        assert res.doi == "10.1109/cvpr.2016.90"
        assert res.external_ids.get("dblp_key") == "conf/cvpr/HeZRS16"

    @pytest.mark.asyncio
    async def test_dblp_corr_extracts_arxiv_id(self, client):
        """DBLP CoRR entry with volume='abs/2404.06395' synthesizes arXiv ID and DOI."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "result": {
                        "hits": {
                            "hit": {
                                "info": {
                                    "title": "MiniCPM: Unveiling the Potential of Small Language Models.",
                                    "authors": {"author": {"text": "Shengding Hu"}},
                                    "venue": "CoRR",
                                    "volume": "abs/2404.06395",
                                    "year": "2024",
                                    "key": "journals/corr/abs-2404-06395",
                                }
                            }
                        }
                    }
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Hu, S. (2024). MiniCPM: Unveiling the Potential of Small Language Models.",
                title="MiniCPM: Unveiling the Potential of Small Language Models",
                authors=["Shengding Hu"],
                year="2024",
            )
            res = await client.lookup(cit)

        assert res.found is True
        assert res.external_ids.get("arxiv") == "2404.06395"
        assert res.doi == "10.48550/arxiv.2404.06395"


# ============================================================
# 2. ArxivClient Tests
# ============================================================


SAMPLE_ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2303.08774v4</id>
    <published>2023-03-15T17:00:00Z</published>
    <title>GPT-4 Technical
      Report</title>
    <summary>We report the development of GPT-4, a large-scale multimodal model.</summary>
    <author><name>OpenAI</name></author>
    <author><name>Josh Achiam</name></author>
  </entry>
</feed>
"""


class TestArxivClient:
    @pytest.fixture
    def client(self):
        return ArxivClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_arxiv_lookup_by_id_from_doi(self, client):
        """ArxivClient extracts arXiv ID from 10.48550/arXiv.* DOI and queries id_list."""
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, text=SAMPLE_ARXIV_ATOM)

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="OpenAI (2023). GPT-4 Technical Report. arXiv:2303.08774.",
                title="GPT-4 Technical Report",
                doi="10.48550/arXiv.2303.08774",
                year="2023",
            )
            res = await client.lookup(cit)

        assert captured_params.get("id_list") == "2303.08774"
        assert res.found is True
        assert res.title == "GPT-4 Technical Report"
        assert res.year == "2023"
        assert res.doi == "10.48550/arxiv.2303.08774"
        assert res.external_ids.get("arxiv") == "2303.08774"
        assert "large-scale multimodal model" in (res.abstract or "")

    @pytest.mark.asyncio
    async def test_arxiv_lookup_by_title_search(self, client):
        """ArxivClient searches by title when no arXiv ID is present."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "search_query" in dict(request.url.params)
            return httpx.Response(200, text=SAMPLE_ARXIV_ATOM)

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="OpenAI (2023). GPT-4 Technical Report.",
                title="GPT-4 Technical Report",
                authors=["OpenAI"],
                year="2023",
            )
            res = await client.lookup(cit)

        assert res.found is True
        assert res.title == "GPT-4 Technical Report"
        assert res.confidence >= 0.90


# ============================================================
# 3. OpenLibraryClient Tests
# ============================================================


class TestOpenLibraryClient:
    @pytest.fixture
    def client(self):
        return OpenLibraryClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_openlibrary_matches_edition_year_and_strips_edition_suffix(self, client):
        """OpenLibrary resolves 'Learning PHP, MySQL & JavaScript, 5th Edition' (2018) using publish_year list."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "docs": [
                        {
                            "key": "/works/OL15000000W",
                            "title": "Learning PHP, MySQL & JavaScript",
                            "author_name": ["Robin Nixon"],
                            "first_publish_year": 2009,
                            "publish_year": [2009, 2012, 2014, 2018, 2021],
                            "publisher": ["O'Reilly Media"],
                            "isbn": ["9781491978917"],
                        }
                    ]
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Robin Nixon (2018). Learning PHP, MySQL & JavaScript, 5th Edition. O'Reilly Media.",
                title="Learning PHP, MySQL & JavaScript, 5th Edition",
                authors=["Robin Nixon"],
                year="2018",
            )
            res = await client.lookup(cit)

        assert res.found is True
        assert res.source_name == "openlibrary"
        assert res.year == "2018"  # Matched 5th edition year from publish_year!
        assert res.authors == ["Robin Nixon"]
        assert res.venue == "O'Reilly Media"
        assert res.external_ids.get("isbn") == "9781491978917"

    @pytest.mark.asyncio
    async def test_openlibrary_falls_back_to_google_books(self, client):
        """When OpenLibrary returns empty docs, OpenLibraryClient falls back to Google Books API."""
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "openlibrary.org" in url:
                return httpx.Response(200, json={"docs": []})
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "gb-flanagan-7e",
                            "volumeInfo": {
                                "title": "JavaScript: The Definitive Guide",
                                "authors": ["David Flanagan"],
                                "publishedDate": "2020-05-14",
                                "publisher": "O'Reilly Media",
                                "infoLink": "https://books.google.com/books?id=gb-flanagan-7e",
                                "industryIdentifiers": [
                                    {"type": "ISBN_13", "identifier": "9781491952023"}
                                ],
                            },
                        }
                    ]
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Flanagan, D. (2020). JavaScript: The Definitive Guide, 7th Edition.",
                title="JavaScript: The Definitive Guide, 7th Edition",
                authors=["David Flanagan"],
                year="2020",
            )
            res = await client.lookup(cit)

        assert res.found is True
        assert res.title == "JavaScript: The Definitive Guide"
        assert res.authors == ["David Flanagan"]
        assert res.year == "2020"
        assert res.external_ids.get("isbn") == "9781491952023"


# ============================================================
# 4. EuropePMCClient Tests
# ============================================================


class TestEuropePMCClient:
    @pytest.fixture
    def client(self):
        return EuropePMCClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_europepmc_lookup_by_doi(self, client):
        """EuropePMC resolves biomedical/psychology paper by DOI with abstract and PMID."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert 'DOI:"10.1046/j.1525-1497.2001.016009606.x"' in str(request.url.params.get("query"))
            return httpx.Response(
                200,
                json={
                    "resultList": {
                        "result": [
                            {
                                "id": "11556941",
                                "pmid": "11556941",
                                "doi": "10.1046/j.1525-1497.2001.016009606.x",
                                "title": "The PHQ-9: validity of a brief depression severity measure.",
                                "authorList": {
                                    "author": [
                                        {"fullName": "Kroenke K"},
                                        {"fullName": "Spitzer RL"},
                                        {"fullName": "Williams JB"},
                                    ]
                                },
                                "pubYear": "2001",
                                "journalTitle": "Journal of General Internal Medicine",
                                "abstractText": "<p>The Patient Health Questionnaire (PHQ-9) is a 9-item depression module.</p>",
                            }
                        ]
                    }
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Kroenke, K., Spitzer, R. L., & Williams, J. B. (2001). The PHQ-9: validity of a brief depression severity measure.",
                title="The PHQ-9: validity of a brief depression severity measure",
                doi="10.1046/j.1525-1497.2001.016009606.x",
                year="2001",
            )
            res = await client.lookup(cit)

        assert res.found is True
        assert res.confidence == 1.0
        assert res.title == "The PHQ-9: validity of a brief depression severity measure"
        assert res.year == "2001"
        assert res.external_ids.get("pmid") == "11556941"
        assert "<p>" not in (res.abstract or "")
