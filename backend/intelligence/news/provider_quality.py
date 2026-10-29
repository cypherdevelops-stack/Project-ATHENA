from __future__ import annotations

from datetime import timedelta
import re
from time import perf_counter

from django.utils import timezone

from .models import NewsProviderQuality


def provider_quota_status(*, provider_name: str, limits: dict, now=None) -> dict:
    now = now or timezone.now()
    period_seconds = int(limits.get('period_seconds', 86400))
    limit = int(limits.get('limit', 0))
    if period_seconds <= 0 or limit <= 0:
        raise ValueError(f'Invalid request quota configured for {provider_name}.')
    window_start = now - timedelta(seconds=period_seconds)
    metrics = NewsProviderQuality.objects.filter(
        provider_name=provider_name,
        observed_at__gte=window_start,
    )
    used = metrics.count()
    latest = metrics.order_by('-observed_at').first()
    rate_limited = bool(
        latest
        and latest.error
        and re.search(r'\b429\b|rate.?limit|quota exceeded', latest.error, re.IGNORECASE)
        and latest.observed_at >= now - timedelta(seconds=min(period_seconds, 60))
    )
    return {
        'limit': limit,
        'periodSeconds': period_seconds,
        'used': used,
        'remaining': 0 if rate_limited else max(0, limit - used),
        'available': used < limit and not rate_limited,
        'rateLimited': rate_limited,
    }


def observe_provider_call(*, provider_name: str, fetch, symbols: list[str]) -> tuple[list[dict], NewsProviderQuality]:
    started = perf_counter()
    try:
        items = fetch(symbols=symbols)
        titles = [str(item.get('title') or item.get('headline') or '').strip().lower() for item in items]
        duplicate_count = len(titles) - len(set(title for title in titles if title))
        metric = NewsProviderQuality.objects.create(
            provider_name=provider_name,
            available=True,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            item_count=len(items),
            duplicate_count=max(duplicate_count, 0),
        )
        return items, metric
    except Exception as error:
        metric = NewsProviderQuality.objects.create(
            provider_name=provider_name,
            available=False,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            error=re.sub(
                r'([?&](?:token|api[-_]?key)=)[^&\s]+',
                r'\1[redacted]',
                str(error),
                flags=re.IGNORECASE,
            )[:500],
        )
        raise


def provider_quality_summary(*, provider_name: str, limit: int = 20) -> dict:
    metrics = list(NewsProviderQuality.objects.filter(provider_name=provider_name).order_by('-observed_at')[:limit])
    if not metrics:
        return {'provider': provider_name, 'observations': 0, 'availability': 0.0, 'averageLatencyMs': None, 'duplicateRate': 0.0}
    available = sum(metric.available for metric in metrics)
    item_count = sum(metric.item_count for metric in metrics)
    duplicates = sum(metric.duplicate_count for metric in metrics)
    latencies = [metric.latency_ms for metric in metrics if metric.latency_ms is not None]
    return {
        'provider': provider_name,
        'observations': len(metrics),
        'availability': round(available / len(metrics), 4),
        'averageLatencyMs': round(sum(latencies) / len(latencies), 3) if latencies else None,
        'duplicateRate': round(duplicates / item_count, 4) if item_count else 0.0,
    }