"""scripts for analyzing SMC features in candle data and detecting entry confirmation signals."""
from __future__ import annotations

from .confirmation import detect_entry_confirmation
from .displacement import detect_displacement_and_mss
from .lifecycle import advance_poi_state
from .liquidity import detect_liquidity_sweeps
from .normalization import normalize_candles
from .structure import detect_structure
from .types import SMCAnalysis, SetupEvidence
from .validation import SMC_SCHEMA_VERSION
from .zones import detect_zones


def analyze_multi_timeframe(*args, **kwargs) -> dict:
    from .multi_timeframe import analyze_multi_timeframe as _analyze_multi_timeframe

    return _analyze_multi_timeframe(*args, **kwargs)


def detect_features(candles: list[dict], timeframe: str) -> SMCAnalysis:
    if len(candles) < 5:
        return {
            'timeframe': timeframe,
            'schemaVersion': SMC_SCHEMA_VERSION,
            'status': 'INSUFFICIENT_DATA',
            'structure': 'UNKNOWN',
            'events': [],
            'orderBlocks': [],
            'fairValueGaps': [],
        }
    normalized = normalize_candles(candles)
    structure, events = detect_structure(normalized)
    order_blocks, fair_value_gaps = detect_zones(normalized)
    return {
        'timeframe': timeframe,
        'schemaVersion': SMC_SCHEMA_VERSION,
        'status': 'READY',
        'structure': structure,
        'events': events,
        'orderBlocks': order_blocks,
        'fairValueGaps': fair_value_gaps,
    }


def detect_setup_evidence(candles: list[dict]) -> SetupEvidence:
    evidence: SetupEvidence = {
        'sell_side_liquidity_swept': False,
        'buy_side_liquidity_swept': False,
        'bullish_displacement': False,
        'bearish_displacement': False,
        'bullish_mss': False,
        'bearish_mss': False,
    }
    if len(candles) < 7:
        return evidence
    normalized = normalize_candles(candles)
    evidence.update(detect_liquidity_sweeps(normalized))
    evidence.update(detect_displacement_and_mss(normalized))
    return evidence


__all__ = [
    'advance_poi_state',
    'analyze_multi_timeframe',
    'detect_entry_confirmation',
    'detect_features',
    'detect_setup_evidence',
]
