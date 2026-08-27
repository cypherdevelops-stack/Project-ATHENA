from __future__ import annotations

from .contracts import NewsEvent, NEWS_CATEGORIES

CATEGORY_TERMS = {
    'CENTRAL_BANK': ('federal reserve', 'fed ', 'fomc', 'ecb', 'boe', 'central bank'),
    'INTEREST_RATES': ('interest rate', 'rate decision', 'rate cut', 'rate hike', 'yield'),
    'INFLATION': ('cpi', 'inflation', 'consumer prices', 'ppi'),
    'EMPLOYMENT': ('nonfarm', 'payroll', 'jobs report', 'unemployment', 'employment'),
    'GDP': ('gdp', 'gross domestic product'),
    'PMI': ('pmi', 'manufacturing activity'),
    'RETAIL_SALES': ('retail sales', 'consumer spending'),
    'ENERGY': ('oil', 'crude', 'natural gas', 'opec', 'energy'),
    'COMMODITIES': ('gold', 'silver', 'copper', 'commodity'),
    'GEOPOLITICAL': ('sanction', 'election', 'geopolitical', 'tension'),
    'WAR_CONFLICT': ('war', 'conflict', 'attack', 'ceasefire', 'missile'),
    'BANKING': ('bank failure', 'banking crisis', 'liquidity'),
    'FINANCIAL_MARKETS': ('stocks', 'equities', 'futures', 'market'),
    'CRYPTO': ('bitcoin', 'ethereum', 'crypto'),
}


def classify_event(event: NewsEvent) -> NewsEvent:
    text = f'{event.headline} {event.summary} {event.body or ""}'.lower()
    category = event.category if event.category in NEWS_CATEGORIES and event.category != 'OTHER' else 'OTHER'
    if category == 'OTHER':
        for candidate, terms in CATEGORY_TERMS.items():
            if any(term in text for term in terms):
                category = candidate
                break
    importance = event.importance if event.importance in {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'} else 'LOW'
    if category in {'CENTRAL_BANK', 'INTEREST_RATES', 'INFLATION', 'EMPLOYMENT', 'GDP'} and importance == 'LOW':
        importance = 'HIGH'
    return NewsEvent(**{**event.__dict__, 'category': category, 'importance': importance, 'event_state': 'CLASSIFIED'})
