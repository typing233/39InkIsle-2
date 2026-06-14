import fitz
from app.importer.parsers.base import BaseParser, BookMetadata


class PdfParser(BaseParser):
    def supports(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(self, file_path: str) -> BookMetadata:
        doc = fitz.open(file_path)
        meta = doc.metadata or {}

        title = meta.get("title") or file_path.rsplit("/", 1)[-1].replace(".pdf", "")
        author = meta.get("author")
        description = meta.get("subject")

        cover_data = None
        cover_ext = "png"
        if doc.page_count > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            cover_data = pix.tobytes("png")

        page_count = doc.page_count
        doc.close()

        return BookMetadata(
            title=title,
            author=author,
            description=description,
            cover_data=cover_data,
            cover_ext=cover_ext,
            page_count=page_count,
        )
