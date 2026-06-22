"""Fetch MusicBrainz genres for neighbours of seed artists (weight >= MIN_WEIGHT).

Appends results to ``internal/data/artist_genres.csv`` using the same
cache format as ``graph_builder.enrich_with_genres``, so subsequent
graph builds pick them up automatically.

Resume behaviour: each entry is written to the CSV immediately after
being fetched, so interrupting (Ctrl-C) and re-running is safe — already
cached entries are skipped automatically.

Run from the project root:
    python -m internal.services.enrich_neighbor_genres
    python -m internal.services.enrich_neighbor_genres --min-weight 3
    python -m internal.services.enrich_neighbor_genres --limit 200
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.data.top100artists import TOP_100_ARTISTS
from internal.services.graph_builder import (
    _append_genre_cache,
    _load_genre_cache,
    _pick_main_genre,
)
from internal.third_party_clients.musicbrainz_client import MusicBrainzClient


def _seed_nodes(G: nx.Graph) -> set[str]:
    seed_names = {a["name"] for a in TOP_100_ARTISTS}
    return {n for n, d in G.nodes(data=True) if d.get("name") in seed_names}


def _target_neighbors(G: nx.Graph, seeds: set[str], min_weight: int = 2) -> list[tuple[str, str]]:
    """Return (mbid, name) for non-seed neighbours with edge weight >= min_weight."""
    seen: set[str] = set()
    targets: list[tuple[str, str]] = []
    for s in seeds:
        for nb, edata in G[s].items():
            if nb in seeds or nb in seen:
                continue
            if (edata.get("weight") or 1) >= min_weight:
                seen.add(nb)
                targets.append((nb, G.nodes[nb].get("name", "")))
    targets.sort(key=lambda t: t[1].lower())
    return targets


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--min-weight", type=int, default=2, metavar="N",
        help="Minimum edge weight to consider a neighbour (default: 2)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Max number of artists to fetch in this run (default: no limit)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    graphml_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"
    cache_path = PROJECT_ROOT / "internal" / "data" / "artist_genres.csv"

    G = nx.read_graphml(graphml_path)
    seeds = _seed_nodes(G)
    targets = _target_neighbors(G, seeds, min_weight=args.min_weight)
    cache = _load_genre_cache(cache_path)

    already = sum(1 for mbid, _ in targets if mbid in cache)
    to_fetch = [(mbid, name) for mbid, name in targets if mbid not in cache]

    print(f"Target neighbours (weight >= {args.min_weight}): {len(targets)}")
    print(f"  Already cached: {already}")
    print(f"  Remaining:      {len(to_fetch)}")

    if args.limit is not None:
        to_fetch = to_fetch[: args.limit]
        print(f"  This run:       {len(to_fetch)} (--limit {args.limit})")

    if not to_fetch:
        print("Nothing to do.")
        return

    client = MusicBrainzClient(user_agent="MC859-Teoria-em-Grafos/0.1")
    total = len(to_fetch)
    errors = 0

    try:
        for i, (mbid, name) in enumerate(to_fetch, 1):
            try:
                artist = client.get_artist(mbid)
            except Exception as exc:
                print(f"[{i:>4}/{total}] {name or mbid}: error: {exc}")
                errors += 1
                continue

            genre = _pick_main_genre(artist)
            _append_genre_cache(cache_path, mbid, name, genre)
            print(f"[{i:>4}/{total}] {name or mbid}: {genre!r}")
    except KeyboardInterrupt:
        fetched = i - 1 - errors
        print(f"\nInterrupted at {i}/{total}. {fetched} fetched this session, {errors} errors.")
        print("Re-run to continue from where you stopped.")
        return

    print(f"\nDone. {total - errors}/{total} fetched, {errors} errors.")


if __name__ == "__main__":
    main()
