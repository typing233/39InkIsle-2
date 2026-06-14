import os
import hashlib
from pathlib import Path

SUPPORTED_EXTENSIONS = {".epub", ".pdf", ".cbz"}


def compute_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def scan_folder(folder_path: str) -> list[dict]:
    results = []
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        return results

    for root, _dirs, files in os.walk(folder):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(root, filename)
                try:
                    file_size = os.path.getsize(full_path)
                    results.append({
                        "file_path": full_path,
                        "file_name": filename,
                        "file_size": file_size,
                        "extension": ext,
                    })
                except OSError:
                    continue

    return results
