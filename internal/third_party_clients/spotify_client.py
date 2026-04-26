"""Wrapper around spotipy with the calls the crawler needs."""

from __future__ import annotations

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str, album_types: str) -> None:
        auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        self._sp = spotipy.Spotify(auth_manager=auth, retries=5, requests_timeout=15)
        self._album_types = album_types

    def get_artist(self, artist_id: str) -> dict:
        return self._sp.artist(artist_id)

    def get_artist_albums(self, artist_id: str) -> list[dict]:
        # /artists/{id}/albums caps limit at 10 without Extended Quota access.
        return self._paginate(
            self._sp.artist_albums(artist_id, album_type=self._album_types, limit=10)
        )

    def get_album_tracks(self, album_id: str) -> list[dict]:
        return self._paginate(self._sp.album_tracks(album_id, limit=50))

    def _paginate(self, first_page: dict) -> list[dict]:
        items = list(first_page["items"])
        page = first_page
        while page.get("next"):
            page = self._sp.next(page)
            items.extend(page["items"])
        return items
