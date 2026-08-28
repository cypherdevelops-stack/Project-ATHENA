from __future__ import annotations

from typing import TypedDict


class Candle(TypedDict, total=False):
    open: float
    close: float
    high: float
    low: float
    time: int | float | str


class SMCAnalysis(TypedDict):
    timeframe: str
    status: str
    structure: str
    events: list[dict]
    orderBlocks: list[dict]
    fairValueGaps: list[dict]


class SetupEvidence(TypedDict):
    sell_side_liquidity_swept: bool
    buy_side_liquidity_swept: bool
    bullish_displacement: bool
    bearish_displacement: bool
    bullish_mss: bool
    bearish_mss: bool
