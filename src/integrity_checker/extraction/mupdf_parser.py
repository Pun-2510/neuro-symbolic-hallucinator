"""PyMuPDF (fitz) parser — default, nhanh, tốt cho text layer."""

from __future__ import annotations

from pathlib import Path

from integrity_checker.extraction.base import BasePDFParser, Document, Page


class MuPdfParser(BasePDFParser):
    """Parser dùng PyMuPDF (`pip install PyMuPDF`).

    # TODO(user): tuần 3 — thêm config dpi cho table extraction, image bbox.
    """

    name = "mupdf"

    def parse(self, file_path: str | Path) -> Document:
        try:
            import fitz  # type: ignore
        except ImportError as e:
            raise ImportError(
                "PyMuPDF chưa cài. Chạy: pip install PyMuPDF"
            ) from e

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        doc = fitz.open(str(path))
        try:
            pages: list[Page] = []
            errors: list[str] = []

            for idx in range(len(doc)):
                try:
                    page = doc[idx]
                    text = page.get_text("text") or ""
                    has_text = len(text.strip()) > 0
                    pages.append(
                        Page(page_num=idx + 1, text=text, has_text_layer=has_text)
                    )
                except Exception as e:  # noqa: BLE001
                    errors.append(f"Page {idx + 1}: {e!s}")

            metadata = dict(doc.metadata or {})
            return Document(
                file_path=str(path),
                num_pages=len(doc),
                pages=pages,
                metadata=metadata,
                parser_used=self.name,
                errors=errors,
            )
        finally:
            doc.close()