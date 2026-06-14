from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class CollectionCreate(BaseModel):
    name: str = Field(max_length=100)


class CollectionUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)


class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    collection_type: str
    is_system: bool
    item_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionItemResponse(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    position: int
    added_at: datetime

    class Config:
        from_attributes = True


class CollectionSyncRequest(BaseModel):
    collection_id: uuid.UUID
    device_id: str
    vector_clock: dict[str, int]
    book_ids: list[uuid.UUID]
