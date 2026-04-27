from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.third_party_clients.musicbrainz_client import MusicBrainzClient


class CollaborationGraphBuilder:
    def __init__(self, tracks_csv_path: Path) -> None:
        self._tracks_csv = tracks_csv_path

    def build(self) -> nx.Graph:
        G = nx.Graph()
        track_counts: dict[str, int] = defaultdict(int)
        names: dict[str, str] = {}

        with self._tracks_csv.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                ids = [a for a in (row.get("all_artist_ids") or "").split(";") if a]
                anames = (row.get("all_artist_names") or "").split(";")
                if not ids:
                    continue

                for idx, aid in enumerate(ids):
                    track_counts[aid] += 1
                    if idx < len(anames) and anames[idx]:
                        names[aid] = anames[idx]

                # Edge for every pair of co-credited artists on the track.
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        u, v = ids[i], ids[j]
                        if G.has_edge(u, v):
                            G[u][v]["weight"] += 1
                        else:
                            G.add_edge(u, v, weight=1)

        # Solo artists (no collaborators) still get a node.
        for aid in track_counts:
            if aid not in G:
                G.add_node(aid)

        for aid in G.nodes():
            G.nodes[aid]["name"] = names.get(aid, "")
            G.nodes[aid]["total_tracks"] = track_counts[aid]
            G.nodes[aid]["main_genre"] = ""
            G.nodes[aid]["degree"] = G.degree(aid)

        return G

    @staticmethod
    def enrich_with_genres(
        G: nx.Graph,
        client: MusicBrainzClient,
        cache_path: Path | None = None,
    ) -> None:
        
        cache = _load_genre_cache(cache_path) if cache_path else {}
        nodes = list(G.nodes(data=True))
        total = len(nodes)
        for i, (mbid, attrs) in enumerate(nodes, 1):
            if attrs.get("main_genre"):
                continue

            if mbid in cache:
                G.nodes[mbid]["main_genre"] = cache[mbid]
                print(
                    f"[{i:>4}/{total}] {attrs.get('name', '?')}: "
                    f"{cache[mbid]!r} (cached)"
                )
                continue

            try:
                artist = client.get_artist(mbid)
            except Exception as exc:
                print(f"[{i:>4}/{total}] {attrs.get('name', '?')}: error: {exc}")
                continue
            genre = _pick_main_genre(artist)
            G.nodes[mbid]["main_genre"] = genre
            cache[mbid] = genre
            if cache_path is not None:
                _append_genre_cache(cache_path, mbid, attrs.get("name", ""), genre)
            print(f"[{i:>4}/{total}] {attrs.get('name', '?')}: {genre!r}")


def _pick_main_genre(artist: dict) -> str:
    """Highest-count genre wins; fall back to top folksonomy tag if no genres."""
    genres = artist.get("genres") or []
    if genres:
        top = max(genres, key=lambda g: g.get("count") or 0)
        return top.get("name", "")
    tags = artist.get("tags") or []
    if tags:
        top = max(tags, key=lambda t: t.get("count") or 0)
        return top.get("name", "")
    return ""


_GENRE_CACHE_FIELDS = ["mbid", "name", "main_genre"]


def _load_genre_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as f:
        return {row["mbid"]: row["main_genre"] for row in csv.DictReader(f)}


def _append_genre_cache(path: Path, mbid: str, name: str, genre: str) -> None:
    new_file = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_GENRE_CACHE_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({"mbid": mbid, "name": name, "main_genre": genre})


def main() -> None:
    ENRICH_GENRES = False  # True = make ~1 MB API call per artist (slow)

    tracks_csv = PROJECT_ROOT / "internal" / "data" / "tracks.csv"
    output_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"

    builder = CollaborationGraphBuilder(tracks_csv)
    G = builder.build()
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if ENRICH_GENRES:
        client = MusicBrainzClient(user_agent="MC859-Teoria-em-Grafos/0.1")
        cache_path = PROJECT_ROOT / "internal" / "data" / "artist_genres.csv"
        builder.enrich_with_genres(G, client, cache_path=cache_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, output_path)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
