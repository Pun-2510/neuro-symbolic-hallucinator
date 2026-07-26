"""Baselines — so sánh với phương pháp đơn giản (đề cương §7.1).

    B0: Link/DOI only          — chỉ check DOI resolve
    B1: Crossref top-1         — lấy top-1 từ Crossref
    B2: Fuzzy matching         — title+author fuzzy score
    B3: Embedding only         — cosine similarity title
    B4: ML classifier          — Logistic Regression / XGBoost
    Proposed: Multi-source + neural + symbolic + abstention

# TODO(user): tuần 16 — implement B0–B4 + so sánh trên gold dataset.
"""

from __future__ import annotations


class BaselineRunner:
    """Stub cho tuần 16–17."""

    def __init__(self) -> None:
        self.available_baselines = ["B0", "B1", "B2", "B3", "B4", "proposed"]

    def run(self, baseline: str, dataset: list) -> dict:
        """Trả dict prediction cho mỗi citation trong dataset."""
        raise NotImplementedError(
            f"Baseline {baseline} chưa implement — TODO tuần 16"
        )