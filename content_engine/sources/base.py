from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawItem:
    source: str
    source_id: str
    url: str
    title: str
    description: str = ""
    thumbnail_url: str | None = None
    duration_sec: int | None = None
    view_count: int | None = None
    like_count: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Source(ABC):
    name: str = "base"

    @abstractmethod
    async def fetch(self, limit: int = 25) -> list[RawItem]:
        ...
