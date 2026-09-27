"""Regression tests for the verdicts route feature decoding.

``_load_matched_sources`` previously had an unreachable second half and
always returned ``None``, so ``GET /essays/{id}/verdicts`` serialised
``matched_sources: null`` and broke clients expecting a list.  The helper now
parses the persisted ``features`` JSON blob and defaults to ``[]``.
"""

from __future__ import annotations

import json

from integrity_checker.api.routes.verdicts import (
    _load_citation_link,
    _load_matched_sources,
)


def test_matched_sources_parsed_from_features_blob():
    blob = json.dumps(
        {
            "matched_sources": [
                {"source_name": "crossref", "found": True},
                {"source_name": "openalex", "found": False},
            ]
        }
    )
    assert _load_matched_sources(blob) == [
        {"source_name": "crossref", "found": True},
        {"source_name": "openalex", "found": False},
    ]


def test_matched_sources_defaults_to_empty_list():
    assert _load_matched_sources(None) == []
    assert _load_matched_sources("") == []
    assert _load_matched_sources("not-json") == []
    # Key missing / wrong type must not leak ``None`` to the response model.
    assert _load_matched_sources(json.dumps({"features": {}})) == []
    assert _load_matched_sources(json.dumps({"matched_sources": "nope"})) == []


def test_citation_link_parsed_and_defaults_to_none():
    link = {"occurrence_id": "occ-1", "reference_id": "ref-1", "status": "matched"}
    assert _load_citation_link(json.dumps({"citation_link": link})) == link
    assert _load_citation_link(None) is None
    assert _load_citation_link("not-json") is None
    assert _load_citation_link(json.dumps({"matched_sources": []})) is None
