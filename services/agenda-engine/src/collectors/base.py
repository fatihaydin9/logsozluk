from abc import ABC, abstractmethod
from typing import List
from ..models import Event


class BaseCollector(ABC):
    """Base class for all event collectors."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def collect(self) -> List[Event]:
        """Collect events from the source."""
        pass

    @abstractmethod
    async def is_duplicate(self, event: Event) -> bool:
        """Check if event already exists."""
        pass
