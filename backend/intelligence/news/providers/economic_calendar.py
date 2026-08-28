from __future__ import annotations

import json
from datetime import datetime
from urllib.request import Request, urlopen

from .json_feed import JsonFeedProvider


class EconomicCalendarProvider(JsonFeedProvider):
    name = 'economic_calendar'

    def fetch_events(self, *, start: datetime, end: datetime) -> list[dict]:
        payload = self._fetch_events_payload(start=start, end=end)
        raw_events = payload if isinstance(payload, list) else payload.get('events', payload.get('calendar', []))
        if not isinstance(raw_events, list):
            raise ValueError('Economic calendar events must be a list.')
        return [self._normalise_calendar_event(event) for event in raw_events if isinstance(event, dict)]

    def _fetch_events_payload(self, *, start: datetime, end: datetime):
        url = self._url_with_query([('start', start.isoformat()), ('end', end.isoformat())])
        request = Request(url, headers=self._headers('application/json'))
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    @staticmethod
    def _normalise_calendar_event(event: dict) -> dict:
        timestamp = event.get('timestamp') or event.get('event_time') or event.get('date') or event.get('datetime')
        return {
            **event,
            'event_id': event.get('event_id') or event.get('id'),
            'title': event.get('title') or event.get('name') or event.get('event'),
            'source': event.get('source') or 'economic_calendar',
            'timestamp': timestamp,
            'published_at': timestamp,
            'importance': str(event.get('importance') or event.get('impact') or 'LOW').upper(),
            'entities': [str(event['currency']).upper()] if event.get('currency') else event.get('entities', []),
            'forecast': event.get('forecast') or event.get('estimate'),
            'actual': event.get('actual'),
            'previous': event.get('previous'),
        }
