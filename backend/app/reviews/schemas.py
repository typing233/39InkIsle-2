from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str | None = None


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    review_text: str | None = None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    book_id: uuid.UUID
    rating: int
    review_text: str | None
    is_visible: bool
    username: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedReviewsResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int
