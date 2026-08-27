from __future__ import annotations

from .json_feed import JsonFeedProvider


class OfficialReleaseProvider(JsonFeedProvider):
    name = 'official_release'
