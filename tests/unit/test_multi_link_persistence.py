"""Regression tests — một occurrence cite NHIỀU reference ("[9, 10]").

Bug gốc (Fix 3 residual): linker trả về đúng 2 ``CitationLink`` cho "[9, 10]"
nhưng mọi tầng phía sau chỉ giữ được MỘT slot:

  ``_build_link_lookup``      dict[key] = link    → link sau đè link trước
  ``Citation.citation_link``  scalar object       → chỉ 1 edge
  ``citation_link_json``      JSON object         → chỉ 1 edge
  API ``citation_link``       object              → chỉ 1 edge
  ``in_text_by_ref``          đọc link_dict[0]    → ref #9 đếm thiếu 1

Các test dưới đây khoá lại cả 5 tầng, cộng thêm tương thích ngược với dữ liệu
v1.8 (JSON object đơn) đã nằm trong DB.
"""

from __future__ import annotations

import json

import pytest

from integrity_checker.linking import CitationLinker
from integrity_checker.models.citation import Citation, CitationStyle, CitationType
from integrity_checker.pipeline.integrity_pipeline import (
    IntegrityPipeline,
    _deserialize_citation,
    _deserialize_citation_link_list,
    _serialize_citation,
    _serialize_citation_link_list,
)

NUMERIC_STYLE = CitationStyle.IEEE


def bib(index: int) -> Citation:
    """A reference-list entry the linker can resolve by numeric index."""
    return Citation(
        raw_text=f"Author{index}. Title {index}. Journal, 2020.",
        citation_type=CitationType.REFERENCE_LIST,
        style=NUMERIC_STYLE,
        numeric_index=index,
        reference_id=f"ref-{index:04d}",
    )


def occurrence(raw: str, occ_id: str) -> Citation:
    return Citation(
        raw_text=raw,
        citation_type=CitationType.NUMERIC,
        style=NUMERIC_STYLE,
        reference_id=occ_id,
    )


@pytest.fixture
def linked():
    """Link "[9, 10]" (plus a single and an unresolvable one) and attach the
    resulting links exactly the way the pipeline does."""
    refs = [bib(i) for i in range(1, 12)]
    body = [
        occurrence("[9, 10]", "occ-0001"),
        occurrence("[3]", "occ-0002"),
        occurrence("[99]", "occ-0003"),
    ]
    result = CitationLinker().link(body, refs)
    multi = IntegrityPipeline._build_link_lookup_multi(result.links)
    for cit in body:
        links = multi.get(cit.reference_id) or []
        if links:
            cit.mapping_status = links[0].status.value
            cit.mapping_confidence = links[0].confidence
            cit.citation_links = list(links)
            cit.citation_link = links[0]
    return body, refs, result, multi


class TestLinkerEmitsEveryEdge:
    def test_two_indices_yield_two_links(self, linked):
        body, _, result, _ = linked
        first = [l for l in result.links if l.occurrence_id == "occ-0001"]
        assert [l.reference_id for l in first] == ["ref-0009", "ref-0010"]

    def test_unresolvable_index_still_emits_missing_edge(self, linked):
        _, _, result, _ = linked
        third = [l for l in result.links if l.occurrence_id == "occ-0003"]
        assert len(third) == 1
        assert third[0].reference_id is None
        assert third[0].status.value == "missing_reference"


class TestMultiLookupDoesNotOverwrite:
    """The bug lived here: dict assignment kept only the LAST link."""

    def test_occurrence_key_keeps_both(self, linked):
        _, _, _, multi = linked
        assert [l.reference_id for l in multi["occ-0001"]] == ["ref-0009", "ref-0010"]

    def test_raw_text_key_keeps_both(self, linked):
        _, _, _, multi = linked
        assert [l.reference_id for l in multi["[9, 10]"]] == ["ref-0009", "ref-0010"]

    def test_single_slot_lookup_still_available(self, linked):
        """``_build_link_lookup`` is kept for callers that only need one edge."""
        _, _, result, _ = linked
        single = IntegrityPipeline._build_link_lookup(result.links)
        assert single["occ-0001"].reference_id in {"ref-0009", "ref-0010"}


class TestCitationCarriesList:
    def test_citation_links_holds_both(self, linked):
        body, *_ = linked
        assert [l.reference_id for l in body[0].citation_links] == ["ref-0009", "ref-0010"]

    def test_scalar_is_first_edge_for_backcompat(self, linked):
        body, *_ = linked
        assert body[0].citation_link.reference_id == "ref-0009"

    def test_single_reference_unchanged(self, linked):
        body, *_ = linked
        assert [l.reference_id for l in body[1].citation_links] == ["ref-0003"]


class TestReportCacheRoundTrip:
    def test_serialize_keeps_both(self, linked):
        body, *_ = linked
        payload = _serialize_citation(body[0])
        assert [d["reference_id"] for d in payload["citation_links"]] == [
            "ref-0009",
            "ref-0010",
        ]

    def test_deserialize_keeps_both(self, linked):
        body, *_ = linked
        restored = _deserialize_citation(_serialize_citation(body[0]))
        assert [l.reference_id for l in restored.citation_links] == [
            "ref-0009",
            "ref-0010",
        ]

    def test_legacy_cache_without_list_field(self):
        """v1.8 cache payload has only the scalar — must still hydrate."""
        payload = {
            "raw_text": "[9]",
            "citation_type": CitationType.NUMERIC.value,
            "style": NUMERIC_STYLE.value,
            "citation_link": {
                "occurrence_id": "occ-0001",
                "reference_id": "ref-0009",
                "status": "matched",
                "confidence": 0.9,
                "method": "numeric_index",
            },
        }
        restored = _deserialize_citation(payload)
        assert [l.reference_id for l in restored.citation_links] == ["ref-0009"]


class TestLinkListJsonHelpers:
    def test_serialize_wraps_bare_link(self, linked):
        body, *_ = linked
        out = _serialize_citation_link_list(body[0].citation_link)
        assert [d["reference_id"] for d in out] == ["ref-0009"]

    def test_serialize_none_is_empty(self):
        assert _serialize_citation_link_list(None) == []

    def test_deserialize_legacy_dict(self):
        out = _deserialize_citation_link_list(
            {"occurrence_id": "occ-0001", "reference_id": "ref-0009", "status": "matched"}
        )
        assert [l.reference_id for l in out] == ["ref-0009"]

    def test_deserialize_garbage_is_empty(self):
        assert _deserialize_citation_link_list("not-a-list") == []
        assert _deserialize_citation_link_list([{"status": "matched"}]) != []  # ref None is a real edge

    def test_deserialize_skips_non_dicts(self):
        out = _deserialize_citation_link_list([{"reference_id": "ref-0009"}, "junk", None])
        assert [l.reference_id for l in out] == ["ref-0009"]


class TestApiSerialization:
    """API payload + ``cited_in_text_count`` — ref #9 must not be counted short."""

    @staticmethod
    def _row(citation: Citation, row_id: int, ctype: str = "in_text"):
        class Row:
            pass

        r = Row()
        r.id = row_id
        r.citation_type = ctype
        r.raw_text = citation.raw_text
        r.style = citation.style.value
        r.page_num = citation.page_num
        r.confidence = 0.9
        r.mapping_status = citation.mapping_status
        r.mapping_confidence = citation.mapping_confidence
        r.citation_link = None
        r.citation_links = []
        r.citation_link_json = (
            json.dumps(_serialize_citation_link_list(citation.citation_links))
            if citation.citation_links
            else None
        )
        return r

    @pytest.fixture
    def rows(self, linked):
        body, refs, *_ = linked
        for i, cit in enumerate(body):
            cit.page_num = i + 1
        out = [self._row(c, i + 1) for i, c in enumerate(body)]
        out += [
            self._row(r, 100 + i, ctype="reference_list")
            for i, r in enumerate(refs)
        ]
        return out

    def test_payload_exposes_list(self, rows):
        from integrity_checker.api.routes.report import _serialize_extracted_citation

        payload = _serialize_extracted_citation(rows[0])
        assert [d["reference_id"] for d in payload["citation_links"]] == [
            "ref-0009",
            "ref-0010",
        ]

    def test_payload_keeps_scalar(self, rows):
        from integrity_checker.api.routes.report import _serialize_extracted_citation

        payload = _serialize_extracted_citation(rows[0])
        assert payload["citation_link"]["reference_id"] == "ref-0009"

    def test_cited_in_text_count_includes_second_ref(self, rows):
        from integrity_checker.api.routes.report import _compute_in_text_citation_index

        in_text_by_ref, _ = _compute_in_text_citation_index(rows)
        assert in_text_by_ref["ref-0009"]["count"] == 1
        assert in_text_by_ref["ref-0010"]["count"] == 1

    def test_missing_reference_creates_no_count(self, rows):
        from integrity_checker.api.routes.report import _compute_in_text_citation_index

        in_text_by_ref, _ = _compute_in_text_citation_index(rows)
        assert None not in in_text_by_ref
        assert len(in_text_by_ref) == 3  # ref-0003, ref-0009, ref-0010

    def test_legacy_single_object_column_reads(self):
        from integrity_checker.api.routes.report import (
            _deserialize_citation_link_json,
            _deserialize_citation_links_json,
        )

        legacy = json.dumps(
            {"occurrence_id": "occ-0001", "reference_id": "ref-0009", "status": "matched"}
        )
        assert _deserialize_citation_links_json(legacy) == [json.loads(legacy)]
        assert _deserialize_citation_link_json(legacy)["reference_id"] == "ref-0009"

    def test_empty_column_reads_as_empty(self):
        from integrity_checker.api.routes.report import _deserialize_citation_links_json

        assert _deserialize_citation_links_json(None) == []
        assert _deserialize_citation_links_json("") == []
        assert _deserialize_citation_links_json("not-json") == []
