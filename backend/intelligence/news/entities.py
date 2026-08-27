from __future__ import annotations

import re

from .contracts import NewsEvent

CURRENCY_TERMS = {
    'USD': ('usd', 'dollar', 'federal reserve', 'fed ', 'us '),
    'EUR': ('eur', 'euro', 'ecb', 'european'),
    'GBP': ('gbp', 'pound', 'sterling', 'bank of england'),
    'JPY': ('jpy', 'yen', 'bank of japan'),
    'CAD': ('cad', 'canadian dollar', 'bank of canada'),
    'AUD': ('aud', 'australian dollar', 'rba'),
    'NZD': ('nzd', 'new zealand dollar', 'rbnz'),
    'CHF': ('chf', 'franc', 'swiss national bank'),
}
ASSET_TERMS = {
    'XAUUSD': ('xauusd', 'gold'),
    'EURUSD': ('eurusd',),
    'GBPUSD': ('gbpusd',),
    'USDJPY': ('usdjpy',),
    'USOIL': ('usoil', 'wti', 'crude oil'),
}


def extract_entities(event: NewsEvent) -> NewsEvent:
    text = f'{event.headline} {event.summary} {event.body or ""}'.lower()
    entities = set(event.entities)
    assets = set(event.affected_assets)
    for entity, terms in CURRENCY_TERMS.items():
        if any(term in text for term in terms):
            entities.add(entity)
    for asset, terms in ASSET_TERMS.items():
        if any(term in text for term in terms):
            assets.add(asset)
    assets.update(_symbols(text))
    return NewsEvent(**{**event.__dict__, 'entities': tuple(sorted(entities)), 'affected_assets': tuple(sorted(assets))})


def _symbols(text: str) -> set[str]:
    return {value.upper() for value in re.findall(r'\b[A-Z]{6}\b', text)}
