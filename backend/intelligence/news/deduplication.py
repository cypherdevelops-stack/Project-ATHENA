from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from difflib import SequenceMatcher

from .contracts import NewsEvent


def cluster_events(events: list[NewsEvent]) -> list[NewsEvent]:
    representatives: list[tuple[NewsEvent, set[str], str]] = []
    result: list[NewsEvent] = []
    for event in events:
        words = _tokens(event.headline)
        matching_cluster = next(
            (cluster_id for representative, representative_words, cluster_id in representatives
             if _same_event(event, words, representative, representative_words)),
            None,
        )
        if matching_cluster is None:
            canonical = f'{event.event_id}:{" ".join(sorted(words))}'
            matching_cluster = hashlib.sha256(f'{event.category}:{canonical}'.encode()).hexdigest()[:16]
            representatives.append((event, words, matching_cluster))
        cluster_id = matching_cluster
        result.append(NewsEvent(**{**event.__dict__, 'event_cluster_id': cluster_id}))
    return result


def _tokens(headline: str) -> set[str]:
    stop_words = {'a', 'an', 'and', 'for', 'in', 'of', 'on', 'the', 'to', 'with'}
    words = re.findall(r'[a-z0-9]+', headline.lower())
    return {word for word in words if word not in stop_words and len(word) > 2}


def _same_event(event: NewsEvent, words: set[str], representative: NewsEvent, representative_words: set[str]) -> bool:
    if event.category != representative.category:
        return False
    if abs(event.timestamp - representative.timestamp) > timedelta(hours=24):
        return False
    entity_overlap = bool(set(event.entities) & set(representative.entities))
    union = words | representative_words
    jaccard = len(words & representative_words) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, ' '.join(sorted(words)), ' '.join(sorted(representative_words))).ratio()
    return jaccard >= 0.5 or (entity_overlap and sequence >= 0.45)
