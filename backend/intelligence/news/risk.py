from __future__ import annotations

from datetime import datetime

from .calendar import event_is_in_window
from .contracts import NewsEvent


def assess_execution_conditions(*, spread: float | None, volatility: str | None, max_spread: float | None = None) -> tuple[bool, tuple[str, ...], str]:
    reasons = []
    if spread is not None and max_spread is not None and spread > max_spread:
        reasons.append('SPREAD_ABNORMAL')
    if str(volatility).upper() in {'HIGH', 'EXTREME', 'VOLATILE'}:
        reasons.append('VOLATILITY_ABNORMAL')
    if reasons:
        return False, tuple(reasons), 'Post-news execution conditions are unsafe.'
    return True, (), 'Execution conditions are within configured limits.'


def analysis_execution_allowed(analysis: dict, *, symbol: str) -> tuple[bool, str]:
    """Read only upstream news decisions; never infer a new trade signal."""
    news = analysis.get('news') or {}
    if news.get('news_locked') is True:
        return False, str(news.get('reason') or 'News risk is locked.')
    conditions = analysis.get('executionConditions') or {}
    if conditions and conditions.get('allowed') is False:
        return False, str(conditions.get('reason') or 'Execution conditions are unsafe.')
    instrument = (news.get('instruments') or {}).get(symbol.upper())
    if isinstance(instrument, dict) and instrument.get('execution_allowed') is False:
        return False, str(instrument.get('reason') or 'Instrument news risk does not permit execution.')
    return True, 'News risk permits this execution path.'


def assess_news_risk(events: list[NewsEvent], *, now: datetime, before_minutes: int = 15, after_minutes: int = 10, fail_closed: bool = True) -> tuple[str, bool, tuple[str, ...]]:
    if not events:
        return ('CLEAR', not fail_closed, ('NO_ACTIVE_NEWS',))
    in_window = [event for event in events if event_is_in_window(event.timestamp, now=now, before_minutes=before_minutes, after_minutes=after_minutes)]
    critical = [event for event in in_window if event.importance == 'CRITICAL']
    high = [event for event in in_window if event.importance == 'HIGH']
    if critical:
        return ('CRITICAL', False, ('CRITICAL_EVENT_WINDOW',))
    if high:
        return ('HIGH', False, ('HIGH_IMPACT_EVENT_WINDOW',))
    if in_window:
        return ('MODERATE', False, ('EVENT_WINDOW_ACTIVE',))
    return ('LOW', True, ('RECENT_NEWS',))
