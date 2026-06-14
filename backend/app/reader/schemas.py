from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ProgressUpdate(BaseModel):
    cfi: str | None = None
    chapter_index: int | None = None
    progress_percent: float | None = None
    device_id: str


class ProgressResponse(BaseModel):
    id: UUID
    book_id: UUID
    cfi: str | None
    chapter_index: int | None
    progress_percent: float | None
    device_id: str
    vector_clock: dict
    updated_at: datetime

    model_config = {"from_attributes": True}


class TOCItem(BaseModel):
    title: str
    href: str
    level: int = 0
