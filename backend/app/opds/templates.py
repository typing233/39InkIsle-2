from datetime import datetime, timezone
from app.books.models import Book


def build_atom_feed(title: str, feed_id: str, entries_xml: str, links_xml: str, updated: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opds="http://opds-spec.org/2010/catalog"
      xmlns:dc="http://purl.org/dc/elements/1.1/">
  <id>{feed_id}</id>
  <title>{title}</title>
  <updated>{updated}</updated>
  {links_xml}
  {entries_xml}
</feed>"""


def build_navigation_entry(title: str, href: str, entry_id: str, content: str = "") -> str:
    return f"""<entry>
    <title>{title}</title>
    <id>{entry_id}</id>
    <link rel="subsection" href="{href}" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
    <content type="text">{content}</content>
  </entry>"""


def build_book_entry(book: Book, base_url: str) -> str:
    updated = book.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if book.updated_at else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    author_xml = ""
    if book.author:
        author_xml = f"<author><name>{_escape(book.author)}</name></author>"

    summary_xml = ""
    if book.description:
        summary_xml = f"<summary>{_escape(book.description[:500])}</summary>"

    mime_map = {"epub": "application/epub+zip", "pdf": "application/pdf", "cbz": "application/x-cbz"}
    mime_type = mime_map.get(book.file_format, "application/octet-stream")

    cover_link = ""
    if book.cover_path:
        cover_link = f'<link rel="http://opds-spec.org/image" href="{base_url}/api/v1/books/{book.id}/cover" type="image/jpeg"/>'

    return f"""<entry>
    <title>{_escape(book.title)}</title>
    <id>urn:uuid:{book.id}</id>
    {author_xml}
    {summary_xml}
    <updated>{updated}</updated>
    <link rel="http://opds-spec.org/acquisition" href="{base_url}/api/v1/books/{book.id}/file" type="{mime_type}"/>
    {cover_link}
    <dc:language>{book.language or 'en'}</dc:language>
  </entry>"""


def build_opds2_publication(book: Book, base_url: str) -> dict:
    mime_map = {"epub": "application/epub+zip", "pdf": "application/pdf", "cbz": "application/x-cbz"}
    pub = {
        "metadata": {
            "@type": "http://schema.org/Book",
            "title": book.title,
            "author": [{"name": book.author}] if book.author else [],
            "language": book.language or "en",
        },
        "links": [
            {"rel": "http://opds-spec.org/acquisition", "href": f"{base_url}/api/v1/books/{book.id}/file", "type": mime_map.get(book.file_format, "application/octet-stream")},
        ],
        "images": [],
    }
    if book.description:
        pub["metadata"]["description"] = book.description[:500]
    if book.cover_path:
        pub["images"].append({"href": f"{base_url}/api/v1/books/{book.id}/cover", "type": "image/jpeg"})
    return pub


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
