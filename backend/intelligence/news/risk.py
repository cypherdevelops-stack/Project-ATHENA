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


def assess_news_risk(events: list[NewsEvent], *, now: datetime, before_minutes: int = 15, after_minutes: int = 10, fail_closed: bool = True) -> tuple[str, bool, tuple[str, ...]]:
    if not events:
        return ('CLEAR', not fail_closed, ('NO_ACTIVE_NEWS',))
   