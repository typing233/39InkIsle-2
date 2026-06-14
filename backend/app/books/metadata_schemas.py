from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class MetadataResponse(BaseModel):
    id: UUID
    book_id: UUID
    source_title: str | None
    source_author: str | None
    source_description: str | None
    source_publisher: str | None
    source_language: str | None
    source_isbn: str | None
    source_publish_date: str | None
    calibrated_title: str | None
    calibrated_author: str | None
    calibrated_description: str | None
    calibrated_publisher: str | None
    calibrated_language: str | None
    calibrated_isbn: str | None
    series_name: str | None
    series_index: str | None
    subjects: dict | None
    identifiers: dict | None
    metadata_source: str | None
    last_calibrated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MetadataCalibrate(BaseModel):
    calibrated_title: str | None = None
    calibrated_author: str | None = None
    calibrated_description: str | None = None
    calibrated_publisher: str | None = None
    calibrated_language: str | None = None
    calibrated_isbn: str | None = None
    series_name: str | None = None
    series_index: str | None = None
