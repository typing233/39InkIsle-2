import pytest


class TestOpds:
    """Test OPDS feed generation and auth."""

    def test_atom_feed_structure(self):
        """Generated Atom XML has required OPDS elements."""
        from app.opds.templates import build_atom_feed, build_book_entry

        xml = build_atom_feed(
            title="Test Library",
            feed_id="urn:test",
            entries_xml="",
            links_xml='<link rel="self" href="/opds" type="application/atom+xml"/>',
            updated="2024-01-01T00:00:00Z",
        )
        assert '<?xml version="1.0"' in xml
        assert '<title>Test Library</title>' in xml
        assert 'xmlns:opds="http://opds-spec.org/2010/catalog"' in xml
        assert '<id>urn:test</id>' in xml

    def test_book_entry_has_acquisition_link(self):
        """Book entries include OPDS acquisition links."""
        from app.opds.templates import build_book_entry
        from unittest.mock import Mock
        from datetime import datetime

        book = Mock()
        book.id = "abc-123"
        book.title = "Test Book"
        book.author = "Test Author"
        book.description = "A short description"
        book.file_format = "epub"
        book.cover_path = "/covers/test.jpg"
        book.language = "en"
        book.updated_at = datetime(2024, 1, 1)

        entry = build_book_entry(book, "http://localhost:8000")
        assert 'rel="http://opds-spec.org/acquisition"' in entry
        assert "application/epub+zip" in entry
        assert "Test Book" in entry
        assert "Test Author" in entry
        assert 'rel="http://opds-spec.org/image"' in entry

    def test_opds2_publication_format(self):
        """OPDS 2.0 publication JSON has correct structure."""
        from app.opds.templates import build_opds2_publication
        from unittest.mock import Mock

        book = Mock()
        book.id = "abc-456"
        book.title = "JSON Book"
        book.author = "JSON Author"
        book.description = "Desc"
        book.file_format = "pdf"
        book.cover_path = "/covers/j.jpg"
        book.language = "fr"

        pub = build_opds2_publication(book, "http://localhost:8000")
        assert pub["metadata"]["title"] == "JSON Book"
        assert pub["metadata"]["language"] == "fr"
        assert pub["links"][0]["type"] == "application/pdf"
        assert len(pub["images"]) == 1

    def test_escape_xml_entities(self):
        """XML special characters are properly escaped."""
        from app.opds.templates import _escape
        assert _escape('A & B <C> "D"') == 'A &amp; B &lt;C&gt; &quot;D&quot;'
