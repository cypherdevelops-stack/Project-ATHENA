from __future__ import annotations

import os


def news_settings() -> dict:
    provider_limits = {
        'finnhub': {
            'period_seconds': 60,
            'limit': int(os.getenv('ATHENA_NEWS_FINNHUB_REQUESTS_PER_MINUTE', '50')),
        },
        'newsapi': {
            'period_seconds': 86400,
            'limit': int(os.getenv('ATHENA_NEWS_NEWSAPI_REQUESTS_PER_DAY', '90')),
        },
        'guardian': {
            'period_seconds': 86400,
            'limit': int(os.getenv('ATHENA_NEWS_GUARDIAN_REQUESTS_PER_DAY', '450')),
        },
        'json_feed': {
            'period_seconds': 86400,
            'limit': int(os.getenv('ATHENA_NEWS_JSON_FEED_REQUESTS_PER_DAY', '900')),
        },
        'rss_feed': {
            'period_seconds': 86400,
            'limit': int(os.getenv('ATHENA_NEWS_RSS_REQUESTS_PER_DAY', '900')),
        },
        'economic_calendar': {
            'period_seconds': 86400,
            'limit': int(os.getenv('ATHENA_NEWS_CALENDAR_REQUESTS_PER_DAY', '450')),
        },
    }
    return {
        'feed_url': os.getenv('ATHENA_NEWS_FEED_URL'),
        'rss_url': os.getenv('ATHENA_NEWS_RSS_URL'),
        'calendar_url': os.getenv('ATHENA_NEWS_CALENDAR_URL'),
        'api_key': os.getenv('ATHENA_NEWS_API_KEY'),
        'api_key_header': os.getenv('ATHENA_NEWS_API_KEY_HEADER', 'Authorization'),
        'finnhub_api_key': os.getenv('NEWS_API_KEY_FINNHUB') or os.getenv('NEWS_API_KEY_FINHUB'),
        'newsapi_api_key': os.getenv('NEWS_API_KEY_NEWSAPI'),
        'guardian_api_key': os.getenv('NEWS_API_KEY_THE_GUARDIAN') or os.getenv('NEWS_API_KEY_THE_GURDIAN'),
        'provider_limits': provider_limits,
        'timeout': float(os.getenv('ATHENA_NEWS_REQUEST_TIMEOUT_SECONDS', '3')),
        'pre_event_blackout_minutes': int(os.getenv('ATHENA_NEWS_PRE_EVENT_BLACKOUT_MINUTES', '15')),
        'post_event_blackout_minutes': int(os.getenv('ATHENA_NEWS_POST_EVENT_BLACKOUT_MINUTES', '10')),
        'high_impact_threshold': float(os.getenv('ATHENA_NEWS_HIGH_IMPACT_THRESHOLD', '0.80')),
        'critical_threshold': float(os.getenv('ATHENA_NEWS_CRITICAL_THRESHOLD', '0.95')),
        'fail_closed': os.getenv('ATHENA_NEWS_FAIL_CLOSED', 'true').lower() == 'true',
        'required_provider_count': max(1, int(os.getenv('ATHENA_NEWS_REQUIRED_PROVIDER_COUNT', '2'))),
    }


SOURCE_RELIABILITY = {
    'official_government': 0.98,
    'central_bank': 0.96,
    'established_financial_news': 0.90,
    'financial_publication': 0.85,
    'aggregator': 0.65,
    'social': 0.30,
}
