from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Callable


@dataclass(frozen=True)
class ScalpEvent:
    type: str
    symbol: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict:
        return {
            'type': self.type,
            'symbol': self.symbol,
            'data': self.data.copy(),
            'timestamp': self.timestamp.isoformat(),
        }


Subscriber = Callable[[ScalpEvent], None]


class ScalpEventBus:
    def __init__(self, *, history_size: int = 200):
        if history_size < 1:
            raise ValueError('history_size must be at least 1.')
        self._history = deque(maxlen=history_size)
        self._subscribers: list[Subscriber] = []
        self._lock = RLock()

    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def publish(self, event: ScalpEvent) -> ScalpEvent:
        with self._lock:
            self._history.append(event)
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            subscriber(event)
        return event

    def recent(self, *, symbol: str | None = None, limit: int | None = None) -> list[ScalpEvent]:
        with self._lock:
            events = list(self._history)
        if symbol is not None:
            events = [event for event in events if event.symbol == symbol]
        return events[-limit:] if limit is not None else events

    def clear(self) -> None:
        with self._lock:
            self._history.clear()


# Process-wide bus used by the execution stream endpoint.
scalp_event_bus = ScalpEventBus()
