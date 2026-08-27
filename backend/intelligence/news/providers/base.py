from __future__ import annotations

from datetime import datetime
from typing import Protocol


class NewsProvider(Protocol):
    name: str

    def fetch_latest(self, *, symbols: list[str]) -> list[dict]: ...


class CalendarProvider(Protocol):
    name: str

    def fetch_events(self, *, start: datetime, end: datetime) -> list[dict]: ...
