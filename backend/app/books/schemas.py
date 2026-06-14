from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date


class BookResponse(BaseModel):
    id: UUID
    title: str
    author: str | None
    description: str | None
    cover_path: str | None
    file_format: str
    file_size: int | None
    language: str | None
    publisher: str | None
    publish_date: date | None
    isbn: str | None
    page_count: int | None
    is_available: bool
    created_at: datetime
    tags: list["TagResponse"] = []

    model_config = {"from_attributes": True}


class TagResponse(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str


class BookSearchParams(BaseModel):
    q: str | None = None
    author: str | None = None
    tag: str | None = None
    format: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


class PaginatedBooksResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
