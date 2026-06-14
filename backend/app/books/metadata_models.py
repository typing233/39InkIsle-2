from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from datetime import datetime
import uuid


class BookMetadata(Base):
    __tablename__ = "book_metadata"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), unique=True, index=True
    )

    # Parsed from file
    source_title: Mapped[str | None] = mapped_column(String(500))
    source_author: Mapped[str | None] = mapped_column(String(500))
    source_description: Mapped[str | None] = mapped_column(Text)
    source_publisher: Mapped[str | None] = mapped_column(String(255))
    source_language: Mapped[str | None] = mapped_column(String(10))
    source_isbn: Mapped[str | None] = mapped_column(String(20))
    source_publish_date: Mapped[str | None] = mapped_column(String(50))

    # Calibrated/overridden by admin
    calibrated_title: Mapped[str | None] = mapped_column(String(500))
    calibrated_author: Mapped[str | None] = mapped_column(String(500))
    calibrated_description: Mapped[str | None] = mapped_column(Text)
    calibrated_publisher: Mapped[str | None] = mapped_column(String(255))
    calibrated_language: Mapped[str | None] = mapped_column(String(10))
    calibrated_isbn: Mapped[str | None] = mapped_column(String(20))

    # Additional structured metadata
    series_name: Mapped[str | None] = mapped_column(String(255))
    series_index: Mapped[str | None] = mapped_column(String(20))
    subjects: Mapped[dict | None] = mapped_column(JSONB)
    identifiers: Mapped[dict | None] = mapped_column(JSONB)

    # Provenance
    metadata_source: Mapped[str | None] = mapped_column(String(50))  # 'epub_opf', 'pdf_info', 'manual', 'openlibrary'
    last_calibrated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_calibrated_at: Mapped[datetime | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
