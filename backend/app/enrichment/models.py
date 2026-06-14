from sqlalchemy import String, Text, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from datetime import datetime
import uuid


class MetadataCache(Base):
    __tablename__ = "metadata_cache"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str | None] = mapped_column(String(255))
    query_key: Mapped[str] = mapped_column(String(512))
    response_data: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        UniqueConstraint("provider", "query_key", name="uq_metadata_cache_provider_query"),
        Index("idx_metadata_cache_expires", "expires_at"),
    )


class Thumbnail(Base):
    __tablename__ = "thumbnails"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    size_variant: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[str] = mapped_column(String(1024))
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("book_id", "size_variant", name="uq_thumbnail_book_size"),
    )


class DeadLetterTask(Base):
    __tablename__ = "dead_letter_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
