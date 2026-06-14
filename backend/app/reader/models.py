from sqlalchemy import String, Integer, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from datetime import datetime
import uuid


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    cfi: Mapped[str | None] = mapped_column(String(500))
    chapter_index: Mapped[int | None] = mapped_column(Integer)
    progress_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    device_id: Mapped[str] = mapped_column(String(100))
    vector_clock: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "device_id", name="uq_progress_user_book_device"),
    )
