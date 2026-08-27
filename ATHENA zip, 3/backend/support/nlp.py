"""Small, local NLP layer for ATHENA Help.

This intentionally uses the Python standard library: it provides predictable
tokenization, normalization, synonym expansion, entity extraction, and intent
scoring without moving user text to a third party service.
"""

from dataclasses import dataclass
import re
import unicodedata


_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?")
_ROUTE_RE = re.compile(r"/(?:dashboard|executioner|orchestration|backtesting|journal|settings)\b", re.IGNORECASE)
_SYMBOL_RE = re.compile(r"\b[A-Z]{3,10}(?:USD|EUR|JPY|GBP)?\b")
_TIMEFRAME_RE = re.compile(r"\b(?:M1|M5|M15|M30|H1|H4|D1|W1)\b", re.IGNORECASE)


@dataclass(frozen=True)
class NlpResult:
    normalized: str
    tokens: tuple[str, ...]
    intent: str
    confidence: float
    entities: dict[str, tuple[str, ...]]
    unsafe: bool


_SYNONYMS = {
    'metatrader': 'mt5', 'metatrader5': 'mt5', 'brokerage': 'broker',
    'trade': 'execution', 'trading': 'execution', 'orders': 'order',
    'charts': 'backtesting', 'historical': 'backtesting', 'logs': 'troubleshooting',
    'stuck': 'troubleshooting', 'broken': 'troubleshooting', 'error': 'troubleshooting',
}

_INTENT_TERMS = {
    'orchestration': {'orchestration': 3, 'orchestrate': 3, 'decision': 2, 'regime': 2, 'scalping': 2, 'day': 1, 'alert': 1},
    'execution': {'execution': 3, 'executioner': 3, 'order': 2, 'position': 2, 'paper': 2, 'demo': 2, 'live': 2, 'guardian': 1},
    'backtesting': {'backtesting': 3, 'backtest': 3, 'replay': 2, 'dataset': 2, 'candle': 2, 'timeframe': 1},
    'accounts': {'account': 3, 'broker': 2, 'mt5': 2, 'handshake': 2, 'server': 1, 'login': 1},
    'journal': {'journal': 3, 'observation': 2, 'session': 2, 'notes': 1},
    'navigation': {'where': 2, 'find': 2, 'navigate': 2, 'screen': 1, 'page': 1, 'sidebar': 2},
    'troubleshooting': {'troubleshooting': 3, 'issue': 2, 'problem': 2, 'failed': 2, 'failure': 2, 'error': 2, 'broken': 2},
}

_UNSAFE_PATTERNS = (
    ('place', 'order'), ('place', 'execution'), ('execute', 'order'), ('execute', 'execution'), ('send', 'order'), ('send', 'execution'),
    ('change', 'risk'), ('disable', 'guardian'), ('bypass', 'safety'),
    ('show', 'password'), ('show', 'credential'),
)


def analyze(text: str) -> NlpResult:
    normalized = unicodedata.normalize('NFKC', text).lower()
    tokens = tuple(_TOKEN_RE.findall(normalized))
    canonical_tokens = tuple(_SYNONYMS.get(token, token) for token in tokens)
    scores = {intent: sum(weight for token, weight in terms.items() if token in canonical_tokens) for intent, terms in _INTENT_TERMS.items()}
    best_intent, best_score = max(scores.items(), key=lambda item: item[1])
    total_score = sum(scores.values())
    if best_score == 0:
        best_intent, confidence = 'general', 0.0
    else:
        confidence = round(best_score / max(total_score, best_score), 2)

    symbols = tuple(dict.fromkeys(match.upper() for match in _SYMBOL_RE.findall(text) if match.upper() not in {'HOW', 'CAN', 'WHAT', 'THE'}))
    timeframes = tuple(dict.fromkeys(match.upper() for match in _TIMEFRAME_RE.findall(text)))
    routes = tuple(dict.fromkeys(match.lower() for match in _ROUTE_RE.findall(text)))
    unsafe = any(all(term in canonical_tokens for term in pattern) for pattern in _UNSAFE_PATTERNS)
    return NlpResult(
        normalized=' '.join(canonical_tokens),
        tokens=canonical_tokens,
        intent=best_intent,
        confidence=confidence,
        entities={'symbols': symbols, 'timeframes': timeframes, 'routes': routes},
        unsafe=unsafe,
    )
