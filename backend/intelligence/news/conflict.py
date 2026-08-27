from __future__ import annotations


def assess_conflict(*, technical_direction: str | None, fundamental_score: float, threshold: float = 0.15) -> tuple[str, bool]:
    technical = (technical_direction or '').upper()
    fundamental = 'BUY' if fundamental_score > threshold else 'SELL' if fundamental_score < -threshold else 'NEUTRAL'
    if technical not in {'BUY', 'SELL'} or fundamental == 'NEUTRAL':
        return ('TECHNICAL_LED' if technical in {'BUY', 'SELL'} else 'UNCERTAIN', False)
    if technical == fundamental:
        return 'ALIGNED', False
    return 'CONFLICT', True
