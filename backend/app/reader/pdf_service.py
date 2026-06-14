import fitz
from pathlib import Path
from fastapi.responses import StreamingResponse, Response
import io


def get_pdf_info(file_path: str) -> dict:
    doc = fitz.open(file_path)
    info = {
        "page_count": doc.page_count,
        "metadata": doc.metadata,
    }
    doc.close()
    return info


def render_pdf_page(file_path: str, page_number: int, dpi: int = 150) -> bytes:
    doc = fitz.open(file_path)
    if page_number < 0 or page_number >= doc.page_count:
        doc.close()
        raise ValueError(f"Page {page_number} out of range (0-{doc.page_count - 1})")

    page = doc[page_number]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def stream_pdf_file(file_path: str) -> StreamingResponse:
    path = Path(file_path)
    file_size = path.stat().st_size

    def iter_file():
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type="application/pdf",
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
        },
    )
