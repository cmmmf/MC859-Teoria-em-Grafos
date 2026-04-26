"""Smoke test: hit MusicBrainz for one artist and print what we get."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.third_party_clients.musicbrainz_client import MusicBrainzClient


def main() -> None:
    client = MusicBrainzClient(
        user_agent="MC859-Teoria-em-Grafos/0.1 ( cirilo.morais@revertai.com.br )",
    )

    name = "John Mayer"
    print(f"--- search_artist({name!r}) ---")
    summary = client.search_artist(name)
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:1200])

    mbid = summary["id"]
    print(f"\n--- get_artist({mbid}) ---")
    artist = client.get_artist(mbid)
    print(json.dumps(artist, indent=2, ensure_ascii=False)[:1500])

    print(f"\n--- get_artist_recordings({mbid}) — first 5 of 10 ---")
    recordings = client.get_artist_recordings(mbid, limit=10)
    print(f"recording-count={recordings.get('recording-count')}")
    for r in recordings.get("recordings", [])[:5]:
        artists = ", ".join(
            c["artist"]["name"]
            for c in r.get("artist-credit", [])
            if isinstance(c, dict) and c.get("artist")
        )
        date = r.get("first-release-date") or "?"
        print(f"  [{date}] {r['title']} — {artists}")


if __name__ == "__main__":
    main()
