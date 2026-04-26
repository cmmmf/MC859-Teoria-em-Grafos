"""Smoke test: hit the Spotify API and print whatever comes back.

Works two ways:
  python -m internal.test.test_spotify_client     (from project root)
  python internal/test/test_spotify_client.py     (anywhere)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.config import Config
from internal.third_party_clients.spotify_client import SpotifyClient


def main() -> None:
    config = Config.load()
    client = SpotifyClient(config.client_id, config.client_secret, config.album_types)

    query = "John Mayer"
    print(f"--- search artist {query!r} ---")
    results = client._sp.search(q=query, type="artist", limit=1)
    artist_summary = results["artists"]["items"][0]
    print(json.dumps(artist_summary, indent=2, ensure_ascii=False))

    artist_id = artist_summary["id"]
    print(f"\n--- get_artist({artist_id}) ---")
    artist = client.get_artist(artist_id)
    print(json.dumps(artist, indent=2, ensure_ascii=False))

    print(f"\n--- get_artist_albums({artist_id}) — first 3 ---")
    albums = client.get_artist_albums(artist_id)[:3]
    for album in albums:
        print(f"  {album['album_type']:7} {album['name']} ({album['id']})")

    if albums:
        album_id = albums[0]["id"]
        print(f"\n--- get_album_tracks({album_id}) — first 3 ---")
        for track in client.get_album_tracks(album_id)[:3]:
            artists = ", ".join(a["name"] for a in track["artists"])
            print(f"  {track['name']} — {artists}")


if __name__ == "__main__":
    main()
