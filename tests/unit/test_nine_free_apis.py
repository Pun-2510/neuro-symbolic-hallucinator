"""Comprehensive unit tests for the 9 Free Scholarly & Technical APIs integrated into CITRA:
1. DataCiteClient (api.datacite.org/dois)
2. DoiRaClient (doi.org/doiRA & CSL-JSON content negotiation)
3. DOAJClient (doaj.org/api)
4. OpenAIREHalClient (api.archives-ouvertes.fr & api.openaire.eu)
5. Retraction Status Detection (OpenAlex & Crossref is_retracted + R-RETRACTED-PAPER)
6. NcbiBiorxivClient (api.biorxiv.org & eutils.ncbi.nlm.nih.gov)
7. Internet Archive Wayback Machine Availability API (LinkValidator ARCHIVED_ALIVE + R-WAYBACK-ARCHIVED)
8. HuggingFaceClient (huggingface.co/api/models, /datasets, /papers + R-HF-VERIFIED)
9. TechStandardClient (rfc-editor.org, datatracker.ietf.org, pypi.org + R-RFC-VERIFIED)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
from integrity_checker.logic.rules import SymbolicRules
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import MatchFeatures, ValidationLabel
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.datacite_client import DataCiteClient
from integrity_checker.retrieval.doaj_client import DOAJClient
from integrity_checker.retrieval.doi_ra_client import DoiRaClient
from integrity_checker.retrieval.huggingface_client import HuggingFaceClient
from integrity_checker.retrieval.link_validator import LinkStatus, LinkValidator
from integrity_checker.retrieval.ncbi_biorxiv_client import NcbiBiorxivClient
from integrity_checker.retrieval.openaire_hal_client import OpenAIREHalClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from integrity_checker.retrieval.tech_standard_client import TechStandardClient


def _patch_httpx(handler):
    async def mock_get(self, url, **kwargs):
        headers = kwargs.get("headers") or {}
        params = kwargs.get("params") or {}
        req = httpx.Request("GET", url, headers=headers, params=params)
        return handler(req)

    return patch.object(httpx.AsyncClient, "get", mock_get)


# ============================================================
# 1. DataCiteClient Tests
# ============================================================


class TestDataCiteClient:
    @pytest.fixture
    def client(self):
        return DataCiteClient(contact_email="test@citra.edu.vn")

    def test_is_datacite_doi_prefixes(self):
        assert DataCiteClient.is_datacite_doi("10.5281/zenodo.7654321") is True
        assert DataCiteClient.is_datacite_doi("https://doi.org/10.6084/m9.figshare.12345") is True
        assert DataCiteClient.is_datacite_doi("10.17605/OSF.IO/ABCDE") is True
        assert DataCiteClient.is_datacite_doi("10.48550/arXiv.1706.03762") is True
        assert DataCiteClient.is_datacite_doi("10.1016/j.compedu.2020.103942") is False

    @pytest.mark.asyncio
    async def test_datacite_lookup_zenodo_doi_success(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "api.datacite.org/dois/10.5281" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "10.5281/zenodo.7654321",
                        "attributes": {
                            "doi": "10.5281/zenodo.7654321",
                            "titles": [
                                {"title": "VN-CiteBench: A Vietnamese Academic Citation Benchmark Dataset"}
                            ],
                            "creators": [
                                {"givenName": "Minh", "familyName": "Nguyen"},
                                {"name": "Tran, Phuoc"},
                            ],
                            "publicationYear": 2024,
                            "publisher": "Zenodo",
                            "url": "https://zenodo.org/record/7654321",
                            "descriptions": [
                                {
                                    "descriptionType": "Abstract",
                                    "description": "<p>This dataset contains 10,000 annotated Vietnamese citations for integrity evaluation.</p>",
                                }
                            ],
                        },
                    }
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Nguyen, M., & Tran, P. (2024). VN-CiteBench: A Vietnamese Academic Citation Benchmark Dataset. Zenodo. https://doi.org/10.5281/zenodo.7654321",
                title="VN-CiteBench: A Vietnamese Academic Citation Benchmark Dataset",
                authors=["Minh Nguyen", "Phuoc Tran"],
                year="2024",
                doi="10.5281/zenodo.7654321",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "datacite"
        assert cand.title == "VN-CiteBench: A Vietnamese Academic Citation Benchmark Dataset"
        assert "Minh Nguyen" in cand.authors
        assert cand.year == "2024"
        assert cand.venue == "Zenodo"
        assert cand.doi == "10.5281/zenodo.7654321"
        assert "10,000 annotated Vietnamese citations" in (cand.abstract or "")

    @pytest.mark.asyncio
    async def test_datacite_lookup_by_title_search(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "attributes": {
                                "doi": "10.6084/m9.figshare.998877",
                                "titles": [{"title": "Open Corpus of Legal Citations in Southeast Asia"}],
                                "creators": [{"givenName": "Hoang", "familyName": "Le"}],
                                "publicationYear": 2023,
                                "publisher": "figshare",
                                "descriptions": [
                                    {
                                        "descriptionType": "Abstract",
                                        "description": "Comprehensive legal citation corpus with statutory links across Southeast Asia.",
                                    }
                                ],
                            }
                        }
                    ]
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Le, H. (2023). Open Corpus of Legal Citations in Southeast Asia. figshare.",
                title="Open Corpus of Legal Citations in Southeast Asia",
                authors=["Hoang Le"],
                year="2023",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.doi == "10.6084/m9.figshare.998877"
        assert "Hoang Le" in cand.authors


# ============================================================
# 2. DoiRaClient Tests (Global DOI Registration Agency + CSL-JSON)
# ============================================================


class TestDoiRaClient:
    @pytest.fixture
    def client(self):
        return DoiRaClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_check_registration_agency_jalc_and_nonexistent(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "10.11499" in url_str:
                return httpx.Response(200, json=[{"DOI": "10.11499/sicejl.58.123", "RA": "JaLC"}])
            return httpx.Response(200, json=[{"DOI": "10.9999/fake.123", "status": "DOI does not exist"}])

        with _patch_httpx(handler):
            ra_jalc = await client.check_registration_agency("10.11499/sicejl.58.123")
            ra_fake = await client.check_registration_agency("10.9999/fake.123")

        assert ra_jalc is not None and ra_jalc.get("RA") == "JaLC"
        assert ra_fake is not None and ra_fake.get("RA") is None

    @pytest.mark.asyncio
    async def test_doi_ra_csl_json_resolution_for_regional_doi(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "doiRA" in url_str:
                return httpx.Response(200, json=[{"DOI": "10.11499/sicejl.58.123", "RA": "JaLC"}])
            assert "citationstyles.csl+json" in request.headers.get("Accept", "")
            return httpx.Response(
                200,
                json={
                    "title": "Control Systems Theory in Japanese Robotics",
                    "author": [
                        {"given": "Kenji", "family": "Tanaka"},
                        {"given": "Yuki", "family": "Sato"},
                    ],
                    "issued": {"date-parts": [[2021, 5, 1]]},
                    "container-title": "Journal of SICE (JaLC)",
                    "DOI": "10.11499/sicejl.58.123",
                    "URL": "https://doi.org/10.11499/sicejl.58.123",
                    "abstract": "An overview of modern control systems in Japanese industrial robotics.",
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Tanaka, K., & Sato, Y. (2021). Control Systems Theory in Japanese Robotics. Journal of SICE. https://doi.org/10.11499/sicejl.58.123",
                title="Control Systems Theory in Japanese Robotics",
                authors=["Kenji Tanaka", "Yuki Sato"],
                year="2021",
                doi="10.11499/sicejl.58.123",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "doi_ra"
        assert cand.title == "Control Systems Theory in Japanese Robotics"
        assert cand.authors == ["Kenji Tanaka", "Yuki Sato"]
        assert cand.year == "2021"
        assert cand.doi == "10.11499/sicejl.58.123"
        assert cand.external_ids.get("doi_ra") == "JaLC"


# ============================================================
# 3. DOAJClient Tests
# ============================================================


class TestDOAJClient:
    @pytest.fixture
    def client(self):
        return DOAJClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_doaj_lookup_open_access_journal(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "doaj.org/api/search/articles/" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "doaj-art-001",
                            "bibjson": {
                                "title": "Digital Transformation in Vietnamese Higher Education",
                                "author": [
                                    {"name": "Nguyen Van An"},
                                    {"name": "Tran Thi Binh"},
                                ],
                                "year": "2023",
                                "journal": {"title": "Ho Chi Minh City Open University Journal of Science"},
                                "identifier": [
                                    {"type": "doi", "id": "10.46223/HCMCOUJS.soci.en.13.1.2023"}
                                ],
                                "link": [
                                    {"type": "fulltext", "url": "https://journalofscience.ou.edu.vn/index.php/soci-en/article/view/2023"}
                                ],
                                "abstract": "This article investigates digital transformation adoption across Vietnamese universities.",
                            },
                        }
                    ]
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Nguyen, V. A., & Tran, T. B. (2023). Digital Transformation in Vietnamese Higher Education. Ho Chi Minh City Open University Journal of Science.",
                title="Digital Transformation in Vietnamese Higher Education",
                authors=["Nguyen Van An", "Tran Thi Binh"],
                year="2023",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "doaj"
        assert cand.title == "Digital Transformation in Vietnamese Higher Education"
        assert cand.authors == ["Nguyen Van An", "Tran Thi Binh"]
        assert cand.year == "2023"
        assert cand.venue == "Ho Chi Minh City Open University Journal of Science"
        assert cand.doi == "10.46223/hcmcoujs.soci.en.13.1.2023"
        assert "digital transformation adoption" in (cand.abstract or "")


# ============================================================
# 4. OpenAIREHalClient Tests
# ============================================================


class TestOpenAIREHalClient:
    @pytest.fixture
    def client(self):
        return OpenAIREHalClient(contact_email="test@citra.edu.vn")

    @pytest.mark.asyncio
    async def test_hal_lookup_doctoral_thesis(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "archives-ouvertes.fr" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "response": {
                            "docs": [
                                {
                                    "docid": 4123456,
                                    "halId_s": "tel-04123456",
                                    "title_s": ["Neuro-Symbolic Verification of Bibliographic Citations in Academic Theses"],
                                    "authFullName_s": ["Jean Dupont", "Marie Curie"],
                                    "producedDateY_i": 2023,
                                    "docType_s": "THESE",
                                    "uri_s": "https://theses.hal.science/tel-04123456",
                                    "abstract_s": [
                                        "This doctoral dissertation introduces a neuro-symbolic framework for verifying academic citations."
                                    ],
                                }
                            ]
                        }
                    },
                )
            return httpx.Response(200, json={"response": {"results": {"result": []}}})

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Dupont, J., & Curie, M. (2023). Neuro-Symbolic Verification of Bibliographic Citations in Academic Theses. Doctoral Thesis, HAL.",
                title="Neuro-Symbolic Verification of Bibliographic Citations in Academic Theses",
                authors=["Jean Dupont", "Marie Curie"],
                year="2023",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "openaire_hal"
        assert cand.title == "Neuro-Symbolic Verification of Bibliographic Citations in Academic Theses"
        assert cand.authors == ["Jean Dupont", "Marie Curie"]
        assert cand.year == "2023"
        assert cand.url == "https://theses.hal.science/tel-04123456"
        assert "doctoral dissertation" in (cand.abstract or "")


# ============================================================
# 5. Retraction Status Detection Tests (OpenAlex, Crossref, NeuroSymbolicChecker)
# ============================================================


class TestRetractionDetection:
    def test_openalex_parses_is_retracted_flag(self):
        client = OpenAlexClient()
        work = {
            "id": "https://openalex.org/W2100000001",
            "title": "Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children",
            "publication_year": 1998,
            "doi": "https://doi.org/10.1016/s0140-6736(97)11096-0",
            "is_retracted": True,
            "authorships": [{"author": {"display_name": "AJ Wakefield"}}],
            "primary_location": {"source": {"display_name": "The Lancet"}},
        }
        cand = client._work_to_candidate(work)
        assert cand is not None
        assert cand.is_retracted is True
        assert cand.external_ids.get("is_retracted") == "true"

    def test_crossref_parses_retraction_update_to_and_relation(self):
        client = CrossrefClient()
        item = {
            "DOI": "10.1016/s0140-6736(20)31180-6",
            "title": ["Hydroxychloroquine or chloroquine with or without a macrolide for treatment of COVID-19"],
            "author": [{"given": "Mandeep R.", "family": "Mehra"}],
            "published-print": {"date-parts": [[2020, 5, 22]]},
            "container-title": ["The Lancet"],
            "update-to": [{"type": "retraction", "DOI": "10.1016/s0140-6736(20)31324-6"}],
        }
        cand = client._message_to_candidate(item)
        assert cand is not None
        assert cand.is_retracted is True
        assert cand.external_ids.get("is_retracted") == "true"

    def test_neuro_symbolic_checker_flags_retracted_paper_with_r_retracted_paper(self):
        checker = NeuroSymbolicChecker(enable_content_alignment=False)
        citation = Citation(
            raw_text="Wakefield, A. J., et al. (1998). Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children. The Lancet. https://doi.org/10.1016/s0140-6736(97)11096-0",
            title="Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children",
            authors=["A. J. Wakefield"],
            year="1998",
            venue="The Lancet",
            doi="10.1016/s0140-6736(97)11096-0",
        )
        retracted_cand = SourceCandidate(
            source_name="openalex",
            found=True,
            title="Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children",
            authors=["A. J. Wakefield"],
            year="1998",
            venue="The Lancet",
            doi="10.1016/s0140-6736(97)11096-0",
            confidence=0.98,
            external_ids={"is_retracted": "true"},
        )
        source_res = SourceResult(
            citation_raw=citation.raw_text,
            candidates=[retracted_cand],
            sources_queried=["openalex", "crossref"],
            sources_succeeded=["openalex", "crossref"],
            sources_failed={},
            is_retracted=True,
        )
        assert source_res.has_retracted_candidate() is True

        verdict = checker.check(citation=citation, source=source_res)

        assert verdict.label == ValidationLabel.METADATA_ERROR
        assert verdict.is_retracted is True
        assert "R-RETRACTED-PAPER" in verdict.triggered_rules
        assert "retracted_paper" in verdict.mismatched_fields
        assert "RETRACTED" in verdict.reasoning.upper()


# ============================================================
# 6. NcbiBiorxivClient Tests (bioRxiv/medRxiv & NCBI E-Utilities)
# ============================================================


class TestNcbiBiorxivClient:
    @pytest.fixture
    def client(self):
        return NcbiBiorxivClient(contact_email="test@citra.edu.vn")

    def test_is_biorxiv_doi(self):
        assert NcbiBiorxivClient.is_biorxiv_doi("10.1101/2023.05.10.540123") is True
        assert NcbiBiorxivClient.is_biorxiv_doi("https://doi.org/10.1101/841239v1") is True
        assert NcbiBiorxivClient.is_biorxiv_doi("10.1038/nature14539") is False

    @pytest.mark.asyncio
    async def test_biorxiv_lookup_resolves_preprint_and_abstract(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "api.biorxiv.org/details/biorxiv/10.1101/2023.05.10.540123" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "collection": [
                        {
                            "doi": "10.1101/2023.05.10.540123",
                            "title": "Single-cell transcriptomic atlas of human neural organoids",
                            "authors": "Smith, J. A.; Chen, L.; Patel, R.",
                            "date": "2023-05-12",
                            "server": "biorxiv",
                            "abstract": "We present a comprehensive single-cell transcriptomic atlas of human neural organoids across developmental stages.",
                        }
                    ]
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Smith, J. A., Chen, L., & Patel, R. (2023). Single-cell transcriptomic atlas of human neural organoids. bioRxiv. https://doi.org/10.1101/2023.05.10.540123v1",
                title="Single-cell transcriptomic atlas of human neural organoids",
                authors=["J. A. Smith", "L. Chen", "R. Patel"],
                year="2023",
                doi="10.1101/2023.05.10.540123v1",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "ncbi_biorxiv"
        assert cand.title == "Single-cell transcriptomic atlas of human neural organoids"
        assert "Smith, J. A." in cand.authors or "J. A. Smith" in cand.authors
        assert cand.year == "2023"
        assert cand.doi == "10.1101/2023.05.10.540123"
        assert "single-cell transcriptomic atlas" in (cand.abstract or "")


# ============================================================
# 7. Wayback Machine Availability API Tests (LinkValidator + Rules)
# ============================================================


class TestWaybackMachineFallback:
    @pytest.mark.asyncio
    async def test_link_validator_rescues_404_via_wayback_machine(self):
        validator = LinkValidator(timeout=3.0, enable_wayback_fallback=True)
        test_url = "https://old-university-lab.edu/papers/tr2019.pdf"
        wayback_snapshot = "https://web.archive.org/web/20220415120000/https://old-university-lab.edu/papers/tr2019.pdf"

        with patch.object(
            httpx.AsyncClient,
            "head",
            new=AsyncMock(return_value=httpx.Response(410, request=httpx.Request("HEAD", test_url))),
        ), patch.object(
            validator,
            "_check_wayback_machine",
            new=AsyncMock(return_value=(wayback_snapshot, "20220415120000")),
        ):
            res = await validator.validate_url(test_url)

        assert res.status == LinkStatus.ARCHIVED_ALIVE
        assert res.status_code == 410
        assert res.archive_url == wayback_snapshot
        assert res.is_broken is False
        assert res.is_valid is True

    @pytest.mark.asyncio
    async def test_link_validator_keeps_dead_link_when_wayback_has_no_snapshot(self):
        validator = LinkValidator(timeout=3.0, enable_wayback_fallback=True)
        test_url = "https://quantum-hallucinated-ai-journal.org/paper999.pdf"

        with patch.object(
            httpx.AsyncClient,
            "head",
            new=AsyncMock(return_value=httpx.Response(410, request=httpx.Request("HEAD", test_url))),
        ), patch.object(
            validator,
            "_check_wayback_machine",
            new=AsyncMock(return_value=(None, None)),
        ):
            res = await validator.validate_url(test_url)

        assert res.status == LinkStatus.DEAD_LINK
        assert res.archive_url is None
        assert res.is_broken is True

    def test_symbolic_rules_triggers_r_wayback_archived(self):
        rules = SymbolicRules()
        cand = SourceCandidate(
            source_name="openalex",
            found=True,
            title="Technical Report on Vietnamese Parsing",
            authors=["T. Nguyen"],
            year="2019",
            confidence=0.92,
        )
        source_res = SourceResult(
            citation_raw="Nguyen, T. (2019). Technical Report on Vietnamese Parsing. https://old-university-lab.edu/papers/tr2019.pdf",
            candidates=[cand],
            sources_queried=["openalex"],
            sources_succeeded=["openalex"],
            sources_failed={},
            url_status="archived_alive",
            url_status_code=404,
            archive_url="https://web.archive.org/web/20220415/https://old-university-lab.edu/papers/tr2019.pdf",
        )
        features = MatchFeatures(
            title_sim_semantic=0.95,
            title_sim_fuzzy=0.96,
            author_jaccard=1.0,
            year_distance=0,
            venue_sim=0.8,
            doi_exact_match=False,
            source_consensus=1,
        )
        out = rules.apply(
            features=features,
            source=source_res,
            citation_year="2019",
            citation_authors=["T. Nguyen"],
            citation_raw=source_res.citation_raw,
        )
        assert "R-WAYBACK-ARCHIVED" in out.triggered_rules
        assert "R-DEAD-URL" not in out.triggered_rules
        assert out.label == ValidationLabel.VERIFIED


# ============================================================
# 8. HuggingFaceClient Tests
# ============================================================


class TestHuggingFaceClient:
    @pytest.fixture
    def client(self):
        return HuggingFaceClient(contact_email="test@citra.edu.vn")

    def test_extract_hf_target(self):
        cit1 = Citation(
            raw_text="VinAI Research (2020). https://huggingface.co/vinai/phobert-base",
            url="https://huggingface.co/vinai/phobert-base",
        )
        assert HuggingFaceClient.extract_hf_target(cit1) == ("models", "vinai/phobert-base")

        cit2 = Citation(
            raw_text="Dataset available at https://huggingface.co/datasets/bkai-foundation-models/vi-alpaca",
            url="https://huggingface.co/datasets/bkai-foundation-models/vi-alpaca",
        )
        assert HuggingFaceClient.extract_hf_target(cit2) == ("datasets", "bkai-foundation-models/vi-alpaca")

    @pytest.mark.asyncio
    async def test_huggingface_model_lookup_success(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "huggingface.co/api/models/vinai/phobert-base" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "id": "vinai/phobert-base",
                    "author": "vinai",
                    "createdAt": "2020-03-15T10:00:00.000Z",
                    "cardData": {
                        "title": "vinai/phobert-base",
                        "description": "PhoBERT: Pre-trained language models for Vietnamese",
                    },
                    "tags": ["pytorch", "roberta", "arxiv:2003.00744"],
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="VinAI Research (2020). vinai/phobert-base. Hugging Face Hub. https://huggingface.co/vinai/phobert-base",
                title="vinai/phobert-base",
                year="2020",
                url="https://huggingface.co/vinai/phobert-base",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "huggingface"
        assert "phobert-base" in (cand.title or "")
        assert cand.year == "2020"
        assert cand.url == "https://huggingface.co/vinai/phobert-base"


# ============================================================
# 9. TechStandardClient Tests (IETF RFC & PyPI)
# ============================================================


class TestTechStandardClient:
    @pytest.fixture
    def client(self):
        return TechStandardClient(contact_email="test@citra.edu.vn")

    def test_extract_rfc_number(self):
        assert TechStandardClient.extract_rfc_number(
            Citation(raw_text="Fielding, R., et al. (2022). RFC 9110: HTTP Semantics.")
        ) == 9110
        assert TechStandardClient.extract_rfc_number(
            Citation(raw_text="RFC 2616", url="https://www.rfc-editor.org/rfc/rfc2616")
        ) == 2616
        assert TechStandardClient.extract_rfc_number(
            Citation(raw_text="TLS 1.3", doi="10.17487/RFC8446")
        ) == 8446
        assert TechStandardClient.extract_rfc_number(
            Citation(raw_text="Normal paper title without RFC")
        ) is None

    @pytest.mark.asyncio
    async def test_lookup_rfc_9110_success(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            assert "rfc-editor.org/rfc/rfc9110.json" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "doc_id": "RFC9110",
                    "title": "HTTP Semantics",
                    "authors": ["R. Fielding", "M. Nottingham", "J. Reschke"],
                    "pub_date": "June 2022",
                    "doi": "10.17487/RFC9110",
                    "abstract": "The Hypertext Transfer Protocol (HTTP) is a stateless application-level protocol for distributed, collaborative, hypertext information systems.",
                },
            )

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Fielding, R., Nottingham, M., & Reschke, J. (2022). RFC 9110: HTTP Semantics. IETF.",
                title="RFC 9110: HTTP Semantics",
                authors=["R. Fielding", "M. Nottingham", "J. Reschke"],
                year="2022",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "tech_standard"
        assert "HTTP Semantics" in (cand.title or "")
        assert cand.authors == ["R. Fielding", "M. Nottingham", "J. Reschke"]
        assert cand.year == "2022"
        assert cand.doi == "10.17487/rfc9110"
        assert "Hypertext Transfer Protocol" in (cand.abstract or "")


# ============================================================
# 10. RetrievalOrchestrator Domain Classification & Tier Routing Tests
# ============================================================


class TestRetrievalOrchestratorNineApisRouting:
    def test_classify_citation_domain_for_new_sources(self):
        # 1. DataCite DOI signal
        cit_zenodo = Citation(
            raw_text="Nguyen, M. (2024). VN-CiteBench Dataset. Zenodo. https://doi.org/10.5281/zenodo.7654321",
            title="VN-CiteBench Dataset",
            doi="10.5281/zenodo.7654321",
        )
        sig_zenodo = RetrievalOrchestrator.classify_citation_domain(cit_zenodo)
        assert sig_zenodo["is_datacite_doi"] is True

        # 2. bioRxiv DOI signal
        cit_biorxiv = Citation(
            raw_text="Smith, J. (2023). Neural Organoids. bioRxiv. https://doi.org/10.1101/2023.05.10.540123",
            title="Neural Organoids",
            doi="10.1101/2023.05.10.540123",
        )
        sig_bio = RetrievalOrchestrator.classify_citation_domain(cit_biorxiv)
        assert sig_bio["is_biorxiv_doi"] is True
        assert sig_bio["is_biomed"] is True

        # 3. IETF RFC signal
        cit_rfc = Citation(
            raw_text="Fielding, R., Nottingham, M., & Reschke, J. (2022). RFC 9110: HTTP Semantics. IETF.",
            title="RFC 9110: HTTP Semantics",
        )
        sig_rfc = RetrievalOrchestrator.classify_citation_domain(cit_rfc)
        assert sig_rfc["is_rfc_or_pypi"] is True

        # 4. Hugging Face Hub signal
        cit_hf = Citation(
            raw_text="Nguyen, D. Q., & Nguyen, A. T. (2020). vinai/phobert-base. Hugging Face Hub. https://huggingface.co/vinai/phobert-base",
            title="vinai/phobert-base",
            url="https://huggingface.co/vinai/phobert-base",
        )
        sig_hf = RetrievalOrchestrator.classify_citation_domain(cit_hf)
        assert sig_hf["is_huggingface"] is True

        # 5. Thesis / HAL signal
        cit_thesis = Citation(
            raw_text="Dupont, J. (2023). Neuro-Symbolic Citation Verification. Doctoral Dissertation, Sorbonne Université, HAL tel-04123456.",
            title="Neuro-Symbolic Citation Verification",
        )
        sig_thesis = RetrievalOrchestrator.classify_citation_domain(cit_thesis)
        assert sig_thesis["is_thesis_or_repo"] is True

        # 6. Regional / Open Access DOAJ signal
        cit_doaj = Citation(
            raw_text="Tran, B. (2023). Digital Transformation in Vietnam. Tạp chí Khoa học Đại học Mở TP.HCM, Open Access.",
            title="Digital Transformation in Vietnam",
            venue="Tạp chí Khoa học Đại học Mở TP.HCM",
        )
        sig_doaj = RetrievalOrchestrator.classify_citation_domain(cit_doaj)
        assert sig_doaj["is_open_access_regional"] is True

        # 7. GitHub Repository & NPM Package signals
        cit_gh = Citation(
            raw_text="Artifex Software (2023). PyMuPDF: Python bindings for MuPDF. GitHub. https://github.com/pymupdf/PyMuPDF",
            title="PyMuPDF: Python bindings for MuPDF",
            url="https://github.com/pymupdf/PyMuPDF",
        )
        assert RetrievalOrchestrator.classify_citation_domain(cit_gh)["is_rfc_or_pypi"] is True

        cit_npm = Citation(
            raw_text="Linsley, T. (2023). @tanstack/react-query: Powerful asynchronous state management. https://www.npmjs.com/package/@tanstack/react-query",
            title="@tanstack/react-query: Powerful asynchronous state management",
            url="https://www.npmjs.com/package/@tanstack/react-query",
        )
        assert RetrievalOrchestrator.classify_citation_domain(cit_npm)["is_rfc_or_pypi"] is True

        # 8. International Technical Standard / Clinical Manual (Wikidata Knowledge Graph) signal
        cit_iso = Citation(
            raw_text="ISO/IEC (2022). ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection.",
            title="ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection",
        )
        assert RetrievalOrchestrator.classify_citation_domain(cit_iso)["is_knowledge_graph"] is True


# ============================================================
# 11. GitHub Public Repositories (CITATION.cff) & NPM Registry Tests
# ============================================================


class TestGitHubAndNpmRegistryInTechStandard:
    @pytest.fixture
    def client(self):
        return TechStandardClient(contact_email="test@citra.edu.vn")

    def test_extract_github_repo_and_reject_reserved_segments(self):
        assert TechStandardClient.extract_github_repo(
            Citation(
                raw_text="PyMuPDF (2024). https://github.com/pymupdf/PyMuPDF",
                url="https://github.com/pymupdf/PyMuPDF",
            )
        ) == "pymupdf/PyMuPDF"
        assert TechStandardClient.extract_github_repo(
            Citation(
                raw_text="Retrieved from https://github.com/undertheseanlp/underthesea/tree/main.",
            )
        ) == "undertheseanlp/underthesea"
        assert TechStandardClient.extract_github_repo(
            Citation(
                raw_text="https://github.com/topics/machine-learning",
                url="https://github.com/topics/machine-learning",
            )
        ) is None

    def test_extract_npm_package_standard_and_scoped(self):
        assert TechStandardClient.extract_npm_package(
            Citation(
                raw_text="Meta (2023). react. https://www.npmjs.com/package/react",
                url="https://www.npmjs.com/package/react",
            )
        ) == "react"
        assert TechStandardClient.extract_npm_package(
            Citation(
                raw_text="TanStack (2024). https://www.npmjs.com/package/@tanstack/react-query",
                url="https://www.npmjs.com/package/@tanstack/react-query",
            )
        ) == "@tanstack/react-query"

    @pytest.mark.asyncio
    async def test_github_repo_lookup_with_citation_cff_enrichment(self, client):
        cff_content = (
            "cff-version: 1.2.0\n"
            'title: "underthesea: Vietnamese NLP Toolkit"\n'
            "doi: 10.5281/zenodo.1122334\n"
            "date-released: 2023-08-15\n"
            "abstract: Open-source Vietnamese Natural Language Processing toolkit.\n"
            "authors:\n"
            "  - family-names: Vu\n"
            "    given-names: Anh\n"
        )

        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "api.github.com/repos/undertheseanlp/underthesea" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "full_name": "undertheseanlp/underthesea",
                        "name": "underthesea",
                        "description": "Vietnamese NLP Toolkit",
                        "html_url": "https://github.com/undertheseanlp/underthesea",
                        "created_at": "2017-04-10T08:00:00Z",
                        "pushed_at": "2024-09-01T12:00:00Z",
                        "owner": {"login": "undertheseanlp"},
                    },
                )
            if "raw.githubusercontent.com/undertheseanlp/underthesea/HEAD/CITATION.cff" in url_str:
                return httpx.Response(200, text=cff_content)
            return httpx.Response(404)

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Vu, A. (2023). underthesea: Vietnamese NLP Toolkit. GitHub. https://github.com/undertheseanlp/underthesea",
                title="underthesea: Vietnamese NLP Toolkit",
                authors=["Anh Vu"],
                year="2023",
                url="https://github.com/undertheseanlp/underthesea",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "tech_standard"
        assert "underthesea" in (cand.title or "")
        assert "Anh Vu" in cand.authors
        assert cand.year == "2023"
        assert cand.doi == "10.5281/zenodo.1122334"
        assert cand.external_ids.get("github_repo") == "undertheseanlp/underthesea"
        assert "Vietnamese Natural Language Processing" in (cand.abstract or "")

        # Verify zero input echoing when a fake title/author/year is attached to a real GitHub URL
        with _patch_httpx(handler):
            fake_cit = Citation(
                raw_text="Einstein, A. (1995). Totally Fake Quantum Blockchain Routing Protocol. https://github.com/undertheseanlp/underthesea",
                title="Totally Fake Quantum Blockchain Routing Protocol",
                authors=["Albert Einstein"],
                year="1995",
                url="https://github.com/undertheseanlp/underthesea",
            )
            cand_real_only = await client.lookup(fake_cit)

        assert "Quantum Blockchain" not in (cand_real_only.title or "")
        assert "Albert Einstein" not in cand_real_only.authors
        assert cand_real_only.year != "1995"
        checker = NeuroSymbolicChecker(enable_content_alignment=False, enable_calibration=False)
        verdict = checker.check(
            fake_cit,
            SourceResult(
                citation_raw=fake_cit.raw_text,
                candidates=[cand_real_only],
                sources_queried=["tech_standard"],
                sources_succeeded=["tech_standard"],
            ),
        )
        assert verdict.label != ValidationLabel.VERIFIED

    @pytest.mark.asyncio
    async def test_github_repo_lookup_404_sets_nonexistent_status(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"message": "Not Found"})

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="FakeOrg (2024). QuantumHyperLLM. https://github.com/fake-org-9999/quantum-hyper-llm",
                title="QuantumHyperLLM",
                year="2024",
                url="https://github.com/fake-org-9999/quantum-hyper-llm",
            )
            cand = await client.lookup(cit)

        assert cand.found is False
        assert cand.external_ids.get("github_status") == "nonexistent"

    @pytest.mark.asyncio
    async def test_npm_lookup_scoped_package_and_404_nonexistent(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "@tanstack/react-query" in url_str or "%40tanstack/react-query" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "name": "@tanstack/react-query",
                        "description": "Hooks for fetching, caching and updating asynchronous data in React",
                        "author": {"name": "Tanner Linsley"},
                        "time": {
                            "created": "2021-09-10T00:00:00.000Z",
                            "modified": "2024-06-01T00:00:00.000Z",
                            "5.0.0": "2023-10-15T00:00:00.000Z",
                        },
                        "homepage": "https://tanstack.com/query",
                    },
                )
            return httpx.Response(404, json={"error": "Not found"})

        with _patch_httpx(handler):
            cit_ok = Citation(
                raw_text="Linsley, T. (2023). @tanstack/react-query: Hooks for fetching, caching and updating asynchronous data in React. NPM. https://www.npmjs.com/package/@tanstack/react-query",
                title="@tanstack/react-query: Hooks for fetching, caching and updating asynchronous data in React",
                authors=["Tanner Linsley"],
                year="2023",
                url="https://www.npmjs.com/package/@tanstack/react-query",
            )
            cand_ok = await client.lookup(cit_ok)

            cit_404 = Citation(
                raw_text="GhostDev (2024). @ghost/hallucinated-router. https://www.npmjs.com/package/@ghost/hallucinated-router",
                title="@ghost/hallucinated-router",
                year="2024",
                url="https://www.npmjs.com/package/@ghost/hallucinated-router",
            )
            cand_404 = await client.lookup(cit_404)

        assert cand_ok.found is True
        assert cand_ok.year == "2023"
        assert "Tanner Linsley" in cand_ok.authors
        assert cand_ok.external_ids.get("npm_package") == "@tanstack/react-query"

        assert cand_404.found is False
        assert cand_404.external_ids.get("npm_status") == "nonexistent"


# ============================================================
# 12. Wikidata Knowledge Graph (WikiCite) & OpenCitations Index (COCI) Tests
# ============================================================


class TestWikidataOpenCitationsClient:
    @pytest.fixture
    def client(self):
        from integrity_checker.retrieval.wikidata_opencitations_client import (
            WikidataOpenCitationsClient,
        )

        return WikidataOpenCitationsClient(contact_email="test@citra.edu.vn")

    def test_extract_standard_or_manual_code(self):
        from integrity_checker.retrieval.wikidata_opencitations_client import (
            WikidataOpenCitationsClient,
        )

        assert (
            WikidataOpenCitationsClient.extract_standard_or_manual_code(
                Citation(raw_text="ISO/IEC 27001:2022 Information security management systems.")
            )
            == "ISO/IEC 27001:2022"
        )
        assert (
            WikidataOpenCitationsClient.extract_standard_or_manual_code(
                Citation(raw_text="NIST SP 800-53 Rev. 5: Security and Privacy Controls.")
            )
            == "NIST SP 800-53"
        )
        assert (
            WikidataOpenCitationsClient.extract_standard_or_manual_code(
                Citation(
                    raw_text="American Psychiatric Association (2013). Diagnostic and Statistical Manual of Mental Disorders (DSM-5)."
                )
            )
            == "DSM-5"
        )
        assert (
            WikidataOpenCitationsClient.extract_standard_or_manual_code(
                Citation(raw_text="World Health Organization (2019). ICD-11 Mortality and Morbidity Statistics.")
            )
            == "ICD-11"
        )

    @pytest.mark.asyncio
    async def test_opencitations_doi_lookup_success(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "opencitations.net/index/api/v2/metadata/doi:" in url_str:
                return httpx.Response(
                    200,
                    json=[
                        {
                            "title": "A Survey on Large Language Models for Code Generation",
                            "author": "Zhang, Wei [omid:ra/111]; Chen, Hao [omid:ra/222]",
                            "pub_date": "2023-07-15",
                            "venue": "ACM Computing Surveys [issn:0360-0300]",
                            "id": "doi:10.1145/3605943 omid:br/060123",
                        }
                    ],
                )
            return httpx.Response(200, json={})

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="Zhang, W., & Chen, H. (2023). A Survey on Large Language Models for Code Generation. ACM Computing Surveys. https://doi.org/10.1145/3605943",
                title="A Survey on Large Language Models for Code Generation",
                authors=["Wei Zhang", "Hao Chen"],
                year="2023",
                doi="10.1145/3605943",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "wikidata_opencitations"
        assert cand.title == "A Survey on Large Language Models for Code Generation"
        assert cand.authors == ["Wei Zhang", "Hao Chen"]
        assert cand.year == "2023"
        assert cand.venue == "ACM Computing Surveys"
        assert cand.doi == "10.1145/3605943"

    @pytest.mark.asyncio
    async def test_wikidata_lookup_iso_27001_standard(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            params = dict(request.url.params)
            action = params.get("action")
            if action == "wbsearchentities":
                return httpx.Response(
                    200,
                    json={
                        "search": [
                            {
                                "id": "Q1334491",
                                "label": "ISO/IEC 27001",
                                "description": "international information security standard published by ISO and IEC",
                            }
                        ]
                    },
                )
            if action == "wbgetentities":
                return httpx.Response(
                    200,
                    json={
                        "entities": {
                            "Q1334491": {
                                "id": "Q1334491",
                                "labels": {"en": {"value": "ISO/IEC 27001"}},
                                "descriptions": {
                                    "en": {
                                        "value": "international information security standard for Information Security Management Systems (ISMS)"
                                    }
                                },
                                "claims": {
                                    "P1476": [
                                        {
                                            "mainsnak": {
                                                "datavalue": {
                                                    "value": {
                                                        "text": "Information security, cybersecurity and privacy protection — Information security management systems — Requirements",
                                                        "language": "en",
                                                    }
                                                }
                                            }
                                        }
                                    ],
                                    "P577": [
                                        {
                                            "mainsnak": {
                                                "datavalue": {
                                                    "value": {"time": "+2022-10-25T00:00:00Z"}
                                                }
                                            }
                                        },
                                        {
                                            "mainsnak": {
                                                "datavalue": {
                                                    "value": {"time": "+2013-10-01T00:00:00Z"}
                                                }
                                            }
                                        },
                                    ],
                                    "P2093": [
                                        {
                                            "mainsnak": {
                                                "datavalue": {
                                                    "value": "International Organization for Standardization (ISO)"
                                                }
                                            }
                                        }
                                    ],
                                },
                            }
                        }
                    },
                )
            return httpx.Response(200, json={})

        with _patch_httpx(handler):
            cit = Citation(
                raw_text="ISO/IEC (2022). ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection — Information security management systems. ISO.",
                title="ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection",
                authors=["ISO/IEC"],
                year="2022",
            )
            cand = await client.lookup(cit)

        assert cand.found is True
        assert cand.source_name == "wikidata_opencitations"
        assert cand.year == "2022"
        assert cand.external_ids.get("wikidata_qid") == "Q1334491"
        assert cand.external_ids.get("standard_code") == "ISO/IEC 27001:2022"


# ============================================================
# 13. Smart SerpAPI Quota Guard, Circuit Breaker & Negative Cache Tests
# ============================================================


class TestSmartSerpApiQuotaGuardAndCircuitBreaker:
    @pytest.mark.asyncio
    async def test_serpapi_quota_guard_skips_paid_api_when_3_free_apis_return_clean_no_results(self):
        """When >= 3 free scholarly APIs return clean HTTP 200 'no results' / 'no title match'
        and 0 APIs suffer a 429/timeout error, RetrievalOrchestrator MUST NOT call SerpAPI.
        """
        from unittest.mock import MagicMock

        def _make_clean_miss_client(name: str):
            m = MagicMock()
            m.name = name
            m.lookup = AsyncMock(
                return_value=SourceCandidate(
                    source_name=name,
                    found=False,
                    error=f"{name}: no results for 'Hallucinated Quantum Essay Transformer'",
                )
            )
            return m

        mock_serp = MagicMock()
        mock_serp.name = "serpapi"
        mock_serp.lookup = AsyncMock(
            return_value=SourceCandidate(source_name="serpapi", found=False, error="SerpApi: no results")
        )

        orch = RetrievalOrchestrator(
            crossref=_make_clean_miss_client("crossref"),
            openalex=_make_clean_miss_client("openalex"),
            dblp=_make_clean_miss_client("dblp"),
            arxiv=_make_clean_miss_client("arxiv"),
            datacite=_make_clean_miss_client("datacite"),
            openaire_hal=_make_clean_miss_client("openaire_hal"),
            wikidata_opencitations=_make_clean_miss_client("wikidata_opencitations"),
            serpapi=mock_serp,
            use_local_db=False,
            enable_link_validation=False,
        )

        cit = Citation(
            raw_text="Kowalski, M. (2024). Hallucinated Quantum Essay Transformer for Deep Neural Grading. IEEE Access.",
            title="Hallucinated Quantum Essay Transformer for Deep Neural Grading",
            authors=["Kowalski, M."],
            year="2024",
            venue="IEEE Access",
        )
        res = await orch.retrieve(cit)

        assert res.candidates == []
        assert "serpapi" not in res.sources_queried
        mock_serp.lookup.assert_not_called()

    @pytest.mark.asyncio
    async def test_serpapi_quota_guard_allows_rescue_when_free_api_suffers_429_rate_limit(self):
        """When a free API fails with a hard error (429 rate limit / timeout), the quota guard
        allows SerpAPI fallback to rescue the citation.
        """
        from unittest.mock import MagicMock

        def _make_client(name: str, err: str):
            m = MagicMock()
            m.name = name
            m.lookup = AsyncMock(
                return_value=SourceCandidate(source_name=name, found=False, error=err)
            )
            return m

        mock_serp = MagicMock()
        mock_serp.name = "serpapi"
        mock_serp.lookup = AsyncMock(
            return_value=SourceCandidate(
                source_name="serpapi",
                found=True,
                title="Rescued Real Paper Under Rate Limit",
                authors=["Tran, M."],
                year="2023",
                confidence=0.88,
            )
        )

        orch = RetrievalOrchestrator(
            crossref=_make_client("crossref", "Crossref: HTTP 429 rate limit exceeded"),
            openalex=_make_client("openalex", "OpenAlex: request timed out"),
            dblp=_make_client("dblp", "DBLP: no results for 'Rescued Real Paper'"),
            arxiv=_make_client("arxiv", "arXiv: no results for 'Rescued Real Paper'"),
            openlibrary=_make_client("openlibrary", "OpenLibrary: no results"),
            datacite=_make_client("datacite", "DataCite: no results for 'Rescued Real Paper'"),
            openaire_hal=_make_client("openaire_hal", "OpenAIRE: no results"),
            wikidata_opencitations=_make_client("wikidata_opencitations", "Wikidata: no results"),
            serpapi=mock_serp,
            use_local_db=False,
            enable_link_validation=False,
        )

        cit = Citation(
            raw_text="Tran, M. (2023). Rescued Real Paper Under Rate Limit. Neural Computation.",
            title="Rescued Real Paper Under Rate Limit",
            authors=["Tran, M."],
            year="2023",
            venue="Neural Computation",
        )
        res = await orch.retrieve(cit)

        mock_serp.lookup.assert_called_once()
        assert "serpapi" in res.sources_succeeded

    @pytest.mark.asyncio
    async def test_serpapi_client_circuit_breaker_and_negative_cache(self):
        """SerpApiClient trips _quota_exhausted on quota error and caches negative queries."""
        from integrity_checker.retrieval.serpapi_client import SerpApiClient

        SerpApiClient._quota_exhausted = False
        SerpApiClient._negative_query_cache.clear()
        client = SerpApiClient(api_key="test-key-123")

        call_count = 0

        class FakeGoogleSearch:
            def __init__(self, params):
                self.params = params

            def get_dict(self):
                nonlocal call_count
                call_count += 1
                q = str(self.params.get("q") or "")
                if "QuotaTripPaper" in q:
                    return {"error": "Your account has run out of searches for this month."}
                return {"organic_results": []}

        with patch("serpapi.GoogleScholarSearch", FakeGoogleSearch):
            cit_neg = Citation(
                raw_text="Smith, J. (2023). NegativeCachePaperTitle.",
                title="NegativeCachePaperTitle",
                authors=["Smith, J."],
                year="2023",
            )
            # First lookup hits GoogleSearch once, caches negative result
            res1 = await client.lookup(cit_neg)
            assert res1.found is False
            assert call_count == 1

            # Second identical lookup is served from negative cache without calling GoogleSearch
            res2 = await client.lookup(cit_neg)
            assert res2.found is False
            assert "cached negative result" in (res2.error or "").lower()
            assert call_count == 1

            # Quota error trips circuit breaker
            cit_quota = Citation(
                raw_text="Smith, J. (2023). QuotaTripPaper.",
                title="QuotaTripPaper",
                authors=["Smith, J."],
                year="2023",
            )
            res3 = await client.lookup(cit_quota)
            assert res3.found is False
            assert SerpApiClient._quota_exhausted is True
            assert call_count == 2

            # Subsequent lookup with a brand-new title is blocked by circuit breaker (no GoogleSearch call)
            cit_after = Citation(
                raw_text="Doe, A. (2022). BrandNewPaperAfterQuotaExhausted.",
                title="BrandNewPaperAfterQuotaExhausted",
                authors=["Doe, A."],
                year="2022",
            )
            res4 = await client.lookup(cit_after)
            assert res4.found is False
            assert "circuit breaker" in (res4.error or "")
            assert call_count == 2

        # Reset class state for other tests
        SerpApiClient._quota_exhausted = False
        SerpApiClient._negative_query_cache.clear()

