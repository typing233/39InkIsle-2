from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ImportFolderCreate(BaseModel):
    path: str
    scan_interval_seconds: int = 300


class ImportFolderUpdate(BaseModel):
    is_active: bool | None = None
    scan_interval_seconds: int | None = None


class ImportFolderResponse(BaseModel):
    id: UUID
    path: str
    is_active: bool
    scan_interval_seconds: int
    last_scanned_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportTaskResponse(BaseModel):
    id: UUID
    folder_id: UUID | None
    file_path: str
    file_name: str
    status: str
    error_message: str | None
    retry_count: int
    book_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportStats(BaseModel):
    total_tasks: int
    pending: int
    processing: int
    completed: int
    failed: int
    skipped: int
