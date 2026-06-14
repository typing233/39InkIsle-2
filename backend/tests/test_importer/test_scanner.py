import pytest
import os
import tempfile
from app.importer.scanner import scan_folder, compute_file_hash


def test_scan_empty_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        results = scan_folder(tmpdir)
        assert results == []


def test_scan_with_epub():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = os.path.join(tmpdir, "test.epub")
        with open(epub_path, "wb") as f:
            f.write(b"fake epub content")

        results = scan_folder(tmpdir)
        assert len(results) == 1
        assert results[0]["file_name"] == "test.epub"
        assert results[0]["extension"] == ".epub"


def test_scan_ignores_unsupported():
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "readme.txt")
        with open(txt_path, "w") as f:
            f.write("hello")

        results = scan_folder(tmpdir)
        assert results == []


def test_scan_nested():
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir)
        pdf_path = os.path.join(subdir, "book.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake pdf")

        results = scan_folder(tmpdir)
        assert len(results) == 1
        assert results[0]["file_name"] == "book.pdf"


def test_compute_hash():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        path = f.name
    try:
        h = compute_file_hash(path)
        assert len(h) == 64
        assert h == compute_file_hash(path)
    finally:
        os.unlink(path)


def test_hash_differs_for_different_content():
    with tempfile.NamedTemporaryFile(delete=False) as f1:
        f1.write(b"content A")
        path1 = f1.name
    with tempfile.NamedTemporaryFile(delete=False) as f2:
        f2.write(b"content B")
        path2 = f2.name
    try:
        assert compute_file_hash(path1) != compute_file_hash(path2)
    finally:
        os.unlink(path1)
        os.unlink(path2)
