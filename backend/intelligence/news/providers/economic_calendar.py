from __future__ import annotations

from .json_feed import JsonFeedProvider


class EconomicCalendarProvider(JsonFeedProvider):
    name = 'economic_calendar'
