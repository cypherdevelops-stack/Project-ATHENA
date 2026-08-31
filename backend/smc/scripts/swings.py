from __future__ import annotations


def swing_indices(candles: list[dict], side: str) -> list[int]:
    if side not in {'high', 'low'}:
        raise ValueError(f'Unsupported swing side: {side}')
    indices = []
    for index in range(2, len(candles) - 2):
        values = [candles[position][side] for position in range(index - 2, index + 3)]
        center = candles[index][side]
        if center == max(values) if side == 'high' else center == min(values):
            indices.append(index)
    return indices
