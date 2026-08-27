from __future__ import annotations

import os


def news_settings() -> dict:
    return {
        'feed_url': os.getenv('ATHENA_NEWS_FEED_URL'),
        'timeout': float(os.getenv('ATHENA_NEWS_REQUEST_TIMEOUT_SECONDS', '3')),
        'pre_event_blackout_minutes': int(os.getenv('ATHENA_NEWS_PRE_EVENT_BLACKOUT_MINUTES', '15')),
        'post_event_blackout_minutes': int(os.getenv('ATHENA_NEWS_POST_EVENT_BLACKOUT_MINUTES', '10')),
        'high_impact_threshold': float(os.getenv('ATHENA_NEWS_HIGH_IMPACT_THRESHOLD', '0.80')),
        'critical_threshold': float(os.getenv('ATHENA_NEWS_CRITICAL_THRESHOLD', '0.95')),
        'fail_closed': os.getenv('ATHENA_NEWS_FAIL_CLOSED', 'true').lower() == 'true',
    }


SOURCE_RELIABILITY = {
    'official_government': 0.98,
    'central_bank': 0.96,
    'established_financial_news': 0.90,
    'financial_publication': 0.85,
    'aggregator': 0.65,
    'social': 0.30,
}
