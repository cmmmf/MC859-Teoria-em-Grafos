"""Wrapper around the MusicBrainz Web Service v2.

- 1 request/second throttle (MusicBrainz hard rule for anonymous traffic).
- Returns the raw JSON dicts the API yields; callers pick what they need.
"""

from __future__ import annotations

import time
from typing import Any

import requests


class MusicBrainzClient:
    BASE_URL = "https://musicbrainz.org/ws/2"
    MIN_INTERVAL_SECONDS = 1.1  # pad above the 1 req/s rule

    def __init__(self, user_agent: str) -> None:
        self._headers = {"User-Agent": user_agent, "Accept": "application/json"}
        self._last_call_at = 0.0

    def search_artist(self, name: str) -> dict | None:
        data = self._get(
            "artist",
            {"query": f'artist:"{name}"', "limit": 1, "fmt": "json"},
        )
        artists = data.get("artists") or []
        return artists[0] if artists else None

    def get_artist(self, mbid: str) -> dict:
        return self._get(f"artist/{mbid}", {"inc": "tags+genres", "fmt": "json"})

    def get_artist_recordings(self, mbid: str, limit: int = 100, offset: int = 0) -> dict:
        return self._get(
            "recording",
            {
                "artist": mbid,
                "inc": "artist-credits+tags",
                "limit": limit,
                "offset": offset,
                "fmt": "json",
            },
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict:
        self._throttle()
        url = f"{self.BASE_URL}/{path}"
        resp = requests.get(url, params=params, headers=self._headers, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < self.MIN_INTERVAL_SECONDS:
            time.sleep(self.MIN_INTERVAL_SECONDS - elapsed)
        self._last_call_at = time.monotonic()
