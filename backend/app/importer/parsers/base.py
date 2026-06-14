from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BookMetadata:
    title: str
    author: str | None = None
    description: str | None = None
    cover_data: bytes | None = None
    cover_ext: str = "jpg"
    language: str | None = None
    publisher: str | None = None
    publish_date: str | None = None
    isbn: str | None = None
    page_count: int | None = None


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> BookMetadata:
        pass

    @abstractmethod
    def supports(self, file_path: str) -> bool:
        pass
