from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from backend.intelligence.news.engine import NewsEngine
from backend.intelligence.news.providers.json_feed import JsonFeedProvider


POSITIVE_WORDS = frozenset({
    'beat', 'bullish', 'growth', 'hawkish', 'optimism', 'positive', 'rally',
    'recovery', 'strong', 'surge', 'support', 'upside', 'gains', 'improves',
})
NEGATIVE_WORDS = frozenset({
    'bearish', 'contraction', 'crisis', 'dovish', 'downside', 'fear', 'loss',
    'recession', 'risk', 'selloff', 'slump', 'weak', 'drop', 'falls',
})
HIGH_IMPACT_WORDS = frozenset({
    'cpi', 'inflation', 'fomc', 'fed', 'interest rate', 'nonfarm', 'jobs report',
    'gdp', 'central bank', 'rate decision',
})


@dataclass(frozen=True)
class HeadlineSentiment:
    title: str
    source: str
    published_at: str | None
    score: float
    label: str
    relevance: float
    high_impact: bool


@dataclass(frozen=True)
class NewsSentiment:
    provider_available: bool
    state: str
    score: float
    label: str
    confidence: float
    news_locked: bool
    reason: str
    headlines: tuple[HeadlineSentiment, ...] = ()

    def as_dict(self) -> dict:
        return {
            **asdict(self),
            'headlines': [asdict(headline) for headline in self.headlines],
        }


def _normalise_headline(item: dict) -> tuple[str, str, str | None] | None:
    title = str(item.get('title') or item.get('headline') or '').strip()
    if not title:
        return None
    return (
        title,
        str(item.get('source') or item.get('publisher') or 'unknown').strip(),
        item.get('published_at') or item.get('publishedAt') or item.get('published'),
    )


def score_headline(title: str, *, symbol: str = '') -> HeadlineSentiment:
    text = title.lower()
    positive = sum(1 for word in POSITIVE_WORDS if word.strip() in text)
    negative = sum(1 for word in NEGATIVE_WORDS if word in text)
    raw_score = max(-1.0, min(1.0, (positive - negative) / 3.0))
    relevance_terms = {symbol.lower(), 'market', 'markets', 'forex', 'gold', 'dollar', 'currency'} - {''}
    relevance = min(1.0, 0.25 + sum(term in text for term in relevance_terms) * 0.15)
    label = 'BULLISH' if raw_score > 0.15 else 'BEARISH' if raw_score < -0.15 else 'NEUTRAL'
    return HeadlineSentiment(title, 'unknown', None, raw_score, label, relevance, any(word in text for word in HIGH_IMPACT_WORDS))


def aggregate_headlines(headlines: list[dict], *, symbol: str = '') -> NewsSentiment:
    scored: list[HeadlineSentiment] = []
    for item in headlines:
        normalised = _normalise_headline(item)
        if not normalised:
            continue
        title, source, published_at = normalised
        result = score_headline(title, symbol=symbol)
        scored.append(HeadlineSentiment(title, source, published_at, result.score, result.label, result.relevance, result.high_impact))
    if not scored:
            return NewsSentiment(True, 'WAIT', 0.0, 'NEUTRAL', 0.0, False, 'No headlines were available.')
    weight = sum(item.relevance for item in scored)
    score = sum(item.score * item.relevance for item in scored) / weight
    high_impact = any(item.high_impact for item in scored)
    label = 'BULLISH' if score > 0.15 else 'BEARISH' if score < -0.15 else 'NEUTRAL'
    locked = high_impact and abs(score) >= 0.5
    return NewsSentiment(True, 'BLOCK' if locked else 'PASS', score, label, min(1.0, weight / len(scored)), locked,
                         'High-impact headlines have reached the news lock threshold.' if locked else 'News sentiment is within the configured execution threshold.', tuple(scored))


def fetch_news_sentiment(*, symbol: str = '', url: str | None = None, timeout: float = 3.0) -> NewsSentiment:
    feed_url = url or os.getenv('ATHENA_NEWS_FEED_URL')
    if not feed_url:
        return NewsEngine().analyze(symbol=symbol)
    return NewsEngine(JsonFeedProvider(feed_url, timeout=timeout)).analyze(symbol=symbol)