"""ExplanationGenerator — sinh giải thích natural-language cho giảng viên."""

from __future__ import annotations

from integrity_checker.models.validation import CitationVerdict, ValidationLabel


class ExplanationGenerator:
    """Tạo câu giải thích ngắn cho mỗi verdict, phù hợp UI + report.

    # TODO(user): tuần 13 — generate Vietnamese explanations theo template,
        thêm danh sách 'hành động gợi ý' cho giảng viên.
    """

    LABEL_VI = {
        ValidationLabel.VERIFIED: "xác minh được",
        ValidationLabel.METADATA_ERROR: "có lỗi metadata",
        ValidationLabel.SUSPECTED_HALLUCINATION: "nghi ngờ ảo giác",
        ValidationLabel.UNRESOLVED: "chưa đủ bằng chứng",
    }

    SUGGESTIONS = {
        ValidationLabel.VERIFIED: [
            "Citation đã được xác minh — không cần hành động thêm.",
        ],
        ValidationLabel.METADATA_ERROR: [
            "Kiểm tra lại các trường bị lệch trong reference list.",
            "Đề nghị sinh viên cung cấp bản PDF nguồn gốc.",
        ],
        ValidationLabel.SUSPECTED_HALLUCINATION: [
            "Không tìm thấy nguồn — cần giảng viên kiểm tra thủ công.",
            "Đề nghị sinh viên cung cấp URL/DOI bản gốc.",
        ],
        ValidationLabel.UNRESOLVED: [
            "Hệ thống chưa đủ bằng chứng để kết luận.",
            "Có thể thử lại sau khi nguồn được cập nhật hoặc cung cấp thêm DOI.",
        ],
    }

    @classmethod
    def short(cls, verdict: CitationVerdict) -> str:
        """One-liner tiếng Việt cho UI."""
        vi_label = cls.LABEL_VI[verdict.label]
        return f"Citation {vi_label} (confidence={verdict.confidence:.0%})."

    @classmethod
    def detailed(cls, verdict: CitationVerdict) -> str:
        """Multi-line explanation cho report."""
        lines = [cls.short(verdict), verdict.reasoning]
        if verdict.mismatched_fields:
            lines.append(f"Trường lệch: {', '.join(verdict.mismatched_fields)}.")
        if verdict.matched_source and verdict.matched_source.best_candidate():
            cand = verdict.matched_source.best_candidate()
            lines.append(
                f"Nguồn tốt nhất: {cand.source_name} — "
                f"title='{cand.title}', year={cand.year}."
            )
        if verdict.triggered_rules:
            lines.append(f"Rules triggered: {', '.join(verdict.triggered_rules)}.")
        return "\n".join(lines)

    @classmethod
    def suggestions(cls, verdict: CitationVerdict) -> list[str]:
        """Gợi ý hành động cho giảng viên."""
        return list(cls.SUGGESTIONS.get(verdict.label, []))