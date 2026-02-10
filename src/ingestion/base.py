from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from src.models import RawEvent, ProjectConfig

class BaseWatcher(ABC):
    def __init__(self, project_name: str, config: ProjectConfig):
        self.project_name = project_name
        self.config = config
        self.last_seen_cursor: Optional[datetime] = None

    @abstractmethod
    def poll(self) -> List[RawEvent]:
        """
        Polls the source for new events since last_seen_cursor.
        Returns a list of RawEvent objects.
        """
        pass

    def update_cursor(self, latest_timestamp: datetime):
        """
        Updates the cursor to the latest timestamp seen.
        """
        if self.last_seen_cursor is None or latest_timestamp > self.last_seen_cursor:
            self.last_seen_cursor = latest_timestamp
