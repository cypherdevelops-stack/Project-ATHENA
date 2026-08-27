from __future__ import annotations


def normalized_surprise(*, actual: float | None, forecast: float | None, scale: float | None = None) -> float:
    if actual is None or forecast is None:
        return 0.0
    denominator = abs(scale or forecast or 1.0)
    return round(max(-1.0, min(1.0, (actual - forecast) / denominator)), 6)
