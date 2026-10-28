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
