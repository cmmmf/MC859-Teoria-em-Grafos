"""Fetch each artist's recordings (and their collaborators) into a CSV.

Source: MusicBrainz. For each artist we resolve the MBID by name (cached),
paginate the artist's recordings, sort client-side by ``first-release-date``
desc, and keep the top ``tracks_per_artist`` (or all of them, if None).

After collecting every artist's rows we deduplicate by
``(normalized title, set of artist MBIDs)`` so live/remaster/EP versions of
the same collaboration collapse to one row — the earliest release wins.

Run from the project root: ``python -m internal.track_fetcher``
                     or:  ``python internal/track_fetcher.py``
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.third_party_clients.musicbrainz_client import MusicBrainzClient


class TrackFetcher:
    CSV_FIELDS = [
        "recording_id",
        "title",
        "first_release_date",
        "primary_artist_id",
        "primary_artist_name",
        "all_artist_ids",
        "all_artist_names",
        "n_artists",
    ]

    PAGE_SIZE = 100  # MusicBrainz max for `/recording` browse

    def __init__(
        self,
        client: MusicBrainzClient,
        tracks_per_artist: int | None = 100,
        max_pages_per_artist: int | None = 5,
    ) -> None:
        """``tracks_per_artist=None`` keeps every recording; ``max_pages_per_artist=None``
        paginates until ``recording-count`` is reached."""
        self._client = client
        self._tracks_per_artist = tracks_per_artist
        self._max_pages_per_artist = max_pages_per_artist

    def fetch_to_csv(
        self,
        artists: Iterable[dict],
        output_path: Path,
        start: int = 1,
        limit: int | None = None,
    ) -> int:
        """Crawl every artist; rewrite the deduped CSV after each one finishes
        so partial progress survives a crash or Ctrl-C.

        ``start`` is 1-based — set to 5 to begin from the 5th artist. If the
        output CSV already exists its rows are preloaded so older artists'
        data is preserved across resumes.
        """
        artists_list = list(artists)
        total_full = len(artists_list)
        end_index = start - 1 + limit if limit is not None else total_full
        slice_to_run = artists_list[start - 1 : end_index]

        rows: list[dict] = self._read_csv(output_path)
        if rows:
            print(f"Resumed from {output_path}: {len(rows)} rows preloaded")

        deduped: list[dict] = self._dedupe(rows) if rows else []
        for offset, artist in enumerate(slice_to_run):
            i = start + offset  # 1-based index in the full artist list
            artist_name = artist["name"]
            mbid = self._resolve_mbid(artist_name)
            if mbid is None:
                print(f"[{i:>3}/{total_full}] {artist_name}: MBID not found, skipping")
                continue

            started = time.monotonic()
            artist_rows = self._fetch_for_artist(mbid, artist_name)
            elapsed = time.monotonic() - started
            rows.extend(artist_rows)

            deduped = self._dedupe(rows)
            self._write_csv(deduped, output_path)

            print(
                f"[{i:>3}/{total_full}] {artist_name} ({mbid}): "
                f"{len(artist_rows)} recordings ({elapsed:.1f}s) "
                f"-> {len(deduped)} unique in CSV"
            )

        return len(deduped)

    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def _resolve_mbid(self, name: str) -> str | None:
        result = self._client.search_artist(name)
        return result["id"] if result else None

    def _fetch_for_artist(self, mbid: str, artist_name: str) -> list[dict]:
        recordings: list[dict] = []
        offset = 0
        page_count = 0
        while True:
            if (
                self._max_pages_per_artist is not None
                and page_count >= self._max_pages_per_artist
            ):
                break
            data = self._client.get_artist_recordings(
                mbid, limit=self.PAGE_SIZE, offset=offset
            )
            page = data.get("recordings") or []
            if not page:
                break
            recordings.extend(page)
            page_count += 1
            total_count = data.get("recording-count", 0)
            offset += self.PAGE_SIZE
            if offset >= total_count:
                break

        # Newest first by first-release-date (lex sort works for YYYY[-MM[-DD]]).
        recordings.sort(key=lambda r: r.get("first-release-date") or "", reverse=True)
        if self._tracks_per_artist is not None:
            recordings = recordings[: self._tracks_per_artist]

        return [self._row(r, mbid, artist_name) for r in recordings]

    @staticmethod
    def _row(recording: dict, primary_id: str, primary_name: str) -> dict:
        # artist-credit alternates dicts and joinphrase strings; keep only dicts
        # that carry a real artist with an MBID.
        credits = [
            c
            for c in (recording.get("artist-credit") or [])
            if isinstance(c, dict) and c.get("artist") and c["artist"].get("id")
        ]
        all_ids = [c["artist"]["id"] for c in credits]
        all_names = [c["artist"]["name"] for c in credits]
        return {
            "recording_id": recording["id"],
            "title": recording.get("title", ""),
            "first_release_date": recording.get("first-release-date") or "",
            "primary_artist_id": primary_id,
            "primary_artist_name": primary_name,
            "all_artist_ids": ";".join(all_ids),
            "all_artist_names": ";".join(all_names),
            "n_artists": len(credits),
        }

    @staticmethod
    def _dedupe(rows: list[dict]) -> list[dict]:
        """Collapse rows that share (normalized title, set of artist IDs).

        Live/remaster/EP versions of the same collaboration produce different
        ``recording_id``s but represent one collaboration — keep the row with
        the earliest ``first_release_date`` so the original release wins.
        """
        by_key: dict[tuple[str, frozenset[str]], dict] = {}
        for row in rows:
            key = (
                row["title"].strip().lower(),
                frozenset(row["all_artist_ids"].split(";"))
                if row["all_artist_ids"]
                else frozenset(),
            )
            existing = by_key.get(key)
            if existing is None or _release_sort_key(row) < _release_sort_key(existing):
                by_key[key] = row
        return list(by_key.values())

    def _write_csv(self, rows: list[dict], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def _release_sort_key(row: dict) -> str:
    # Empty dates sort last so any real date beats an unknown one.
    return row.get("first_release_date") or "9999"


def main() -> None:
    from internal.data.top100artists import TOP_100_ARTISTS

    START_FROM_ARTIST = 87                  # 1-based; e.g. 5 to resume from artist #5
    ARTIST_LIMIT: int | None = None            # how many artists to process from `start`
    TRACKS_PER_ARTIST: int | None = 3000    # None = keep every recording
    MAX_PAGES_PER_ARTIST: int | None = None # None = paginate to the end

    client = MusicBrainzClient(user_agent="MC859-Teoria-em-Grafos/0.1")
    fetcher = TrackFetcher(
        client,
        tracks_per_artist=TRACKS_PER_ARTIST,
        max_pages_per_artist=MAX_PAGES_PER_ARTIST,
    )

    output_path = PROJECT_ROOT / "internal" / "data" / "tracks.csv"
    n = fetcher.fetch_to_csv(
        TOP_100_ARTISTS, output_path, start=START_FROM_ARTIST, limit=ARTIST_LIMIT
    )
    print(f"\nWrote {n} unique recordings to {output_path}")


if __name__ == "__main__":
    main()
