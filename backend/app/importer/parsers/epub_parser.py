import ebooklib
from ebooklib import epub
from app.importer.parsers.base import BaseParser, BookMetadata


class EpubParser(BaseParser):
    def supports(self, file_path: str) -> bool:
        return file_path.lower().endswith(".epub")

    def parse(self, file_path: str) -> BookMetadata:
        book = epub.read_epub(file_path)

        title = book.get_metadata("DC", "title")
        title = title[0][0] if title else "Unknown"

        creator = book.get_metadata("DC", "creator")
        author = creator[0][0] if creator else None

        description_meta = book.get_metadata("DC", "description")
        description = description_meta[0][0] if description_meta else None

        language_meta = book.get_metadata("DC", "language")
        language = language_meta[0][0] if language_meta else None

        publisher_meta = book.get_metadata("DC", "publisher")
        publisher = publisher_meta[0][0] if publisher_meta else None

        identifier_meta = book.get_metadata("DC", "identifier")
        isbn = None
        if identifier_meta:
            for ident in identifier_meta:
                val = ident[0]
                if val and (val.startswith("978") or val.startswith("979")):
                    isbn = val
                    break

        cover_data = None
        cover_ext = "jpg"
        for item in book.get_items_of_type(ebooklib.ITEM_COVER):
            cover_data = item.get_content()
            if item.file_name.endswith(".png"):
                cover_ext = "png"
            break

        if not cover_data:
            for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                if "cover" in (item.file_name or "").lower():
                    cover_data = item.get_content()
                    if item.file_name.endswith(".png"):
                        cover_ext = "png"
                    break

        return BookMetadata(
            title=title,
            author=author,
            description=description,
            cover_data=cover_data,
            cover_ext=cover_ext,
            language=language,
            publisher=publisher,
            isbn=isbn,
        )
