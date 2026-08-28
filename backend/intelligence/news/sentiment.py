from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import NewsEvent

POSITIVE = frozenset({'beat', 'bullish', 'growth', 'hawkish', 'optimism', 'positive', 'rally', 'recovery', 'strong', 'surge', 'support', 'upside', 'gains', 'improves'})
NEGATIVE = frozenset({'bearish', 'contraction', 'crisis', 'dovish', 'downside', 'fear', 'loss', 'recession', 'risk', 'selloff', 'slump', 'weak', 'drop', 'fall', 'falls', 'fell'})
NEGATIONS = frozenset({'not', 'no', 'less', 'lower', 'fails', 'failed', 'without'})


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float
    confidence: float
    model_name: str = 'rule_based_financial'
    model_version: str = '1'


class FinancialSentimentModel(Protocol):
    name: str
    version: str

    def analyze(self, event: NewsEvent) -> SentimentResult: ...


class RuleBasedSentimentModel:
    name = 'rule_based_financial'
    version = '1'

    def analyze(self, event: NewsEvent) -> SentimentResult:
        words = f'{event.headline} {event.summary} {event.body or ""}'.lower().replace('-', ' ').split()
        positive = 0
        negative = 0
        for index, word in enumerate(words):
            previous = words[max(0, index - 3):index]
            if word in POSITIVE:
                positive += -1 if any(item in NEGATIONS for item in previous) else 1
            if word in NEGATIVE:
                negative += -1 if any(item in NEGATIONS for item in previous) else 1
        total = positive + negative
        if total == 0:
            return SentimentResult('NEUTRAL', 0.0, 0.25, self.name, self.version)
        score = max(-1.0, min(1.0, (positive - negative) / max(3, abs(positive) + abs(negative))))
        label = 'BULLISH' if score > 0.15 else 'BEARISH' if score < -0.15 else 'MIXED'
        confidence = min(1.0, 0.35 + abs(score) * 0.5 + min(0.15, total * 0.03))
        return SentimentResult(label, score, confidence, self.name, self.version)


def analyze_sentiment(event: NewsEvent, model: FinancialSentimentModel | None = None) -> SentimentResult:
    model = model or RuleBasedSentimentModel()
    try:
        return model.analyze(event)
    except Exception:
        return RuleBasedSentimentModel().analyze(event)
