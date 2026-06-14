import zipfile
import re
from pathlib import Path
import mimetypes


def natural_sort_key(s: str) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def get_cbz_info(file_path: str) -> dict:
    pages = list_cbz_pages(file_path)
    return {
        "page_count": len(pages),
        "pages": [{"name": p, "index": i} for i, p in enumerate(pages)],
    }


def list_cbz_pages(file_path: str) -> list[str]:
    with zipfile.ZipFile(file_path, "r") as zf:
        entries = []
        for name in zf.namelist():
            if name.startswith("__MACOSX") or name.startswith("."):
                continue
            ext = Path(name).suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                entries.append(name)
        entries.sort(key=natural_sort_key)
        return entries


def extract_cbz_page(file_path: str, page_index: int) -> tuple[bytes, str]:
    pages = list_cbz_pages(file_path)
    if page_index < 0 or page_index >= len(pages):
        raise ValueError(f"Page {page_index} out of range (0-{len(pages) - 1})")

    page_name = pages[page_index]
    mime_type = mimetypes.guess_type(page_name)[0] or "image/jpeg"

    with zipfile.ZipFile(file_path, "r") as zf:
        data = zf.read(page_name)

    return data, mime_type
