import pytest
from app.reader.cbz_service import natural_sort_key, list_cbz_pages, get_cbz_info, extract_cbz_page
from app.reader.pdf_service import get_pdf_info, render_pdf_page
import zipfile
import tempfile
from pathlib import Path


class TestCbzReader:
    """Test CBZ page extraction with natural sort order."""

    def test_natural_sort_key(self):
        """Natural sort handles mixed numeric/alpha filenames."""
        names = ["page2.jpg", "page10.jpg", "page1.jpg", "page11.jpg", "page3.jpg"]
        sorted_names = sorted(names, key=natural_sort_key)
        assert sorted_names == ["page1.jpg", "page2.jpg", "page3.jpg", "page10.jpg", "page11.jpg"]

    def test_natural_sort_complex(self):
        """Natural sort handles complex naming patterns."""
        names = ["ch1_p02.png", "ch1_p1.png", "ch1_p10.png", "ch2_p1.png"]
        sorted_names = sorted(names, key=natural_sort_key)
        assert sorted_names == ["ch1_p1.png", "ch1_p02.png", "ch1_p10.png", "ch2_p1.png"]

    def test_cbz_info(self, tmp_path):
        """get_cbz_info returns correct page count and names."""
        cbz_path = tmp_path / "test.cbz"
        with zipfile.ZipFile(cbz_path, "w") as zf:
            zf.writestr("page3.jpg", b"\xff\xd8\xff")
            zf.writestr("page1.jpg", b"\xff\xd8\xff")
            zf.writestr("page2.jpg", b"\xff\xd8\xff")
            zf.writestr("readme.txt", b"not an image")

        info = get_cbz_info(str(cbz_path))
        assert info["page_count"] == 3
        assert info["pages"][0]["name"] == "page1.jpg"
        assert info["pages"][2]["name"] == "page3.jpg"

    def test_extract_cbz_page(self, tmp_path):
        """extract_cbz_page returns correct bytes and MIME type."""
        cbz_path = tmp_path / "test.cbz"
        test_content = b"\x89PNG\r\n\x1a\n"
        with zipfile.ZipFile(cbz_path, "w") as zf:
            zf.writestr("img001.png", test_content)
            zf.writestr("img002.jpg", b"\xff\xd8\xff")

        data, mime = extract_cbz_page(str(cbz_path), 0)
        assert data == test_content
        assert mime == "image/png"

    def test_extract_page_out_of_range(self, tmp_path):
        """Accessing out-of-range page raises ValueError."""
        cbz_path = tmp_path / "test.cbz"
        with zipfile.ZipFile(cbz_path, "w") as zf:
            zf.writestr("page1.jpg", b"\xff\xd8\xff")

        with pytest.raises(ValueError, match="out of range"):
            extract_cbz_page(str(cbz_path), 5)

    def test_macosx_files_excluded(self, tmp_path):
        """__MACOSX entries and hidden files are excluded."""
        cbz_path = tmp_path / "test.cbz"
        with zipfile.ZipFile(cbz_path, "w") as zf:
            zf.writestr("page1.jpg", b"\xff\xd8\xff")
            zf.writestr("__MACOSX/._page1.jpg", b"metadata")
            zf.writestr(".DS_Store", b"junk")

        info = get_cbz_info(str(cbz_path))
        assert info["page_count"] == 1
