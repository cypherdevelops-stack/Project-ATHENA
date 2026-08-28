"""
Unified SMC context builder.

Combines multi-timeframe SMC analysis into a single context object
that can be shared across scalping, day trading, and orchestration.
"""
from __future__ import annotations

from typing import Any

from backend.smc.scripts.analyzer import analyze_multi_timeframe
from backend.smc.scripts.lifecycle import active_pois, advance_poi_state


def build_smc_context(
    *,
    candles_by_timeframe: dict[str, list[dict]],
    current_price: float,
    timeframes: tuple[str, ...] = ('H4', 'H1', 'M15', 'M5', 'M1'),
) -> dict[str, Any]:
    """
    Build a full SMC context from candle data.

    Args:
        candles_by_timeframe: Dict mapping timeframe -> list of candles
        current_price: Current market price for POI state advancement
        timeframes: Which timeframes to include (order matters for precedence)

    Returns:
        Dict with per-timeframe analyses, alignment, active POIs, etc.
    """
    # Run multi-timeframe analyzer
    analysis = analyze_multi_timeframe(
        candles_by_timeframe,
        timeframes=timeframes,
        current_time=None,  # Optional; we'll let freshness default
    )

    # Advance all POI states against current price
    for timeframe, tf_analysis in analysis['timeframes'].items():
        for poi_type in ('orderBlocks', 'fairValueGaps'):
            pois = tf_analysis.get(poi_type, [])
            updated = []
            for poi in pois:
                advanced = advance_poi_state(poi, current_price)
                updated.append(advanced)
            tf_analysis[poi_type] = updated
        tf_analysis['activePois'] = active_pois([
            *tf_analysis.get('orderBlocks', []),
            *tf_analysis.get('fairValueGaps', []),
        ])

    return analysis


def extract_smc_evidence(
    smc_context: dict[str, Any],
    *,
    primary_timeframe: str = 'M1',
    secondary_timeframe: str = 'M5',
    higher_timeframe: str = 'H1',
) -> dict[str, Any]:
    """
    Extract the most relevant SMC evidence for a given strategy.

    Used by scalping and day trading to quickly access evidence
    without re-parsing the full context.
    """
    tf_analysis = smc_context.get('timeframes', {})
    primary = tf_analysis.get(primary_timeframe, {})
    secondary = tf_analysis.get(secondary_timeframe, {})
    higher = tf_analysis.get(higher_timeframe, {})

    # Combine POIs from primary and secondary that are active
    active_pois = [
        *primary.get('activePois', []),
        *secondary.get('activePois', []),
    ]

    return {
        'htf_structure': higher.get('structure', 'UNKNOWN'),
        'htf_bias': higher.get('bias', 'UNKNOWN'),
        'ltf_structure': primary.get('structure', 'UNKNOWN'),
        'ltf_bias': primary.get('bias', 'UNKNOWN'),
        'active_pois': active_pois,
        'liquidity': primary.get('liquidity', {}),
        'alignment': smc_context.get('alignment', 'UNKNOWN'),
        'events': primary.get('events', []),
        'interpretation': smc_context.get('interpretation', ''),
    }