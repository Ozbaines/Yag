from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared.db import Draft


@dataclass
class PublishResult:
    success: bool
    remote_id: str | None = None
    remote_url: str | None = None
    error: str | None = None


class Channel(ABC):
    target: str = "base"

    @abstractmethod
    async def publish(self, draft: Draft) -> PublishResult:
        ...
