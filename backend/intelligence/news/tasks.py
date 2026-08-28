from __future__ import annotations

from datetime import datetime, timezone

from backend.accounts.models import Account

from .config import news_settings
from .engine import NewsEngine
from .persistence import persist_news_snapshot


def poll_news_for_account(*, account, now: datetime | None = None) -> dict:
    """Refresh one account's news context; this function never submits orders."""
    symbol = account.canonical_asset or account.broker_symbol or 'XAUUSD'
    result = NewsEngine(settings=news_settings()).analyze(symbol=symbol, now=now or datetime.now(timezone.utc))
    analysis = {'status': 'READY', 'news': result.as_dict()}
    snapshot = persist_news_snapshot(account=account, analysis=analysis)
    return {
        'status': result.state,
        'symbol': symbol,
        'snapshotId': str(snapshot.snapshot_id) if snapshot else None,
        'providerAvailable': result.provider_available,
        'newsRisk': (result.for_symbol(symbol).event_risk),
        'reason': result.reason,
    }


def poll_enabled_accounts(*, account_id: int | None = None, now: datetime | None = None) -> list[dict]:
    accounts = Account.objects.filter(enabled=True)
    if account_id is not None:
        accounts = accounts.filter(pk=account_id)
    return [poll_news_for_account(account=account, now=now) for account in accounts]