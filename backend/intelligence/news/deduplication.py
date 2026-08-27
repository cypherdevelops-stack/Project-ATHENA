from __future__ import annotations

import hashlib
import re

from .contracts import NewsEvent


def cluster_events(events: list[NewsEvent]) -> list[NewsEvent]:
    clusters: dict[str, str] = {}
    result = []
    for event in events:
        key = re.sub(r'[^a-z0-9 ]', '', event.headline.lower())
        words = ' '.join(key.split()[:8])
        cluster_id = clusters.setdefault(words, hashlib.sha256(words.encode()).hexdigest()[:16])
        result.append(NewsEvent(**{**event.__dict__, 'event_cluster_id': cluster_id}))
    return result
