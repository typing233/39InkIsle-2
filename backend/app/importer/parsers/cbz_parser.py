import zipfile
import os
from app.importer.parsers.base import BaseParser, BookMetadata


class CbzParser(BaseParser):
    def supports(self, file_path: str) -> bool:
        return file_path.lower().endswith(".cbz")

    def parse(self, file_path: str) -> BookMetadata:
        title = os.path.basename(file_path).replace(".cbz", "").replace(".CBZ", "")

        cover_data = None
        cover_ext = "jpg"
        page_count = 0

        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

        with zipfile.ZipFile(file_path, "r") as zf:
            image_files = sorted(
                [n for n in zf.namelist() if os.path.splitext(n)[1].lower() in image_exts]
            )
            page_count = len(image_files)

            if image_files:
                first_image = image_files[0]
                cover_data = zf.read(first_image)
                ext = os.path.splitext(first_image)[1].lower()
                cover_ext = ext.lstrip(".")

        return BookMetadata(
            title=title,
            cover_data=cover_data,
            cover_ext=cover_ext,
            page_count=page_count,
        )
