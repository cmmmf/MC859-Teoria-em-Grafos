"""Render ``collab_graph.graphml`` as an interactive HTML page via PyVis.

Node size scales with ``degree``; node color is hashed from ``main_genre``
(stable per genre, so the same genre is always the same color across runs).
Hover over a node to see its full attributes.

Run from the project root: ``python -m internal.services.graph_visualizer``
                     or:  ``python internal/services/graph_visualizer.py``
"""

from __future__ import annotations

import colorsys
import hashlib
import sys
from pathlib import Path

import networkx as nx
from pyvis.network import Network

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.services.graph_builder import CollaborationGraphBuilder
from internal.third_party_clients.musicbrainz_client import MusicBrainzClient


# Visualization knobs — tweak as needed.
TOP_N_NODES: int | None = 100     # keep only top-N by degree (None = ignore)
MIN_DEGREE = 3                   # used only when TOP_N_NODES is None
ENRICH_GENRES = True             # fetch main_genre via MB API for filtered nodes
SIZE_BY = "degree"               # "degree" or "total_tracks"
MIN_NODE_SIZE = 6
MAX_NODE_SIZE = 50
DEFAULT_COLOR = "#888888"        # nodes without main_genre
EDGE_COLOR = "#cccccc"
SHOW_LABELS_FOR_TOP_N = 50       # only label the most-connected nodes
PHYSICS_ITERATIONS = 200         # stop the layout after N steps


def render(graphml_path: Path, output_html: Path) -> None:
    G = nx.read_graphml(graphml_path)
    print(f"Loaded {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if TOP_N_NODES is not None:
        keep = {n for n, _ in sorted(G.degree(), key=lambda x: -x[1])[:TOP_N_NODES]}
        G = G.subgraph(keep).copy()
        print(
            f"Filtered (top {TOP_N_NODES} by degree): "
            f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
        )
    elif MIN_DEGREE > 0:
        keep = [n for n, d in G.degree() if d >= MIN_DEGREE]
        G = G.subgraph(keep).copy()
        print(
            f"Filtered (degree >= {MIN_DEGREE}): "
            f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
        )

    if ENRICH_GENRES:
        client = MusicBrainzClient(user_agent="MC859-Teoria-em-Grafos/0.1")
        cache_path = PROJECT_ROOT / "internal" / "data" / "artist_genres.csv"
        CollaborationGraphBuilder.enrich_with_genres(G, client, cache_path=cache_path)

    sizes = _scaled_sizes(G, attr=SIZE_BY)
    top_nodes = _top_n_by_degree(G, SHOW_LABELS_FOR_TOP_N)

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#1a1a1a",
        font_color="white",
        notebook=False,
        cdn_resources="in_line",
    )
    # Stop the simulation after a fixed budget so the page doesn't melt the CPU.
    net.set_options(
        f"""
        {{
          "physics": {{
            "barnesHut": {{
              "gravitationalConstant": -15000,
              "centralGravity": 0.1,
              "springLength": 120,
              "springConstant": 0.04,
              "damping": 0.5
            }},
            "stabilization": {{
              "enabled": true,
              "iterations": {PHYSICS_ITERATIONS},
              "fit": true
            }},
            "minVelocity": 0.5
          }},
          "interaction": {{ "hover": true, "tooltipDelay": 100 }}
        }}
        """
    )

    for node, attrs in G.nodes(data=True):
        name = attrs.get("name") or node
        genre = attrs.get("main_genre") or ""
        title = (
            f"<b>{name}</b><br>"
            f"degree: {attrs.get('degree', 0)}<br>"
            f"total_tracks: {attrs.get('total_tracks', 0)}<br>"
            f"main_genre: {genre or '—'}<br>"
            f"mbid: {node}"
        )
        net.add_node(
            node,
            label=name if node in top_nodes else "",
            title=title,
            value=sizes[node],
            color=_color_for_genre(genre),
        )

    for u, v, edge_attrs in G.edges(data=True):
        net.add_edge(u, v, value=edge_attrs.get("weight", 1), color=EDGE_COLOR)

    output_html.parent.mkdir(parents=True, exist_ok=True)
    # PyVis's write_html opens the file with the platform default encoding —
    # on Windows that's cp1252, which can't encode names like "Beyoncé". Bypass
    # it: render to a string and write UTF-8 ourselves.
    html = net.generate_html(notebook=False)
    output_html.write_text(html, encoding="utf-8")
    print(f"Wrote {output_html}")


def _scaled_sizes(G: nx.Graph, attr: str) -> dict[str, float]:
    raw = {n: int(G.nodes[n].get(attr) or 0) for n in G.nodes()}
    if not raw:
        return {}
    lo, hi = min(raw.values()), max(raw.values())
    if hi == lo:
        return {n: (MIN_NODE_SIZE + MAX_NODE_SIZE) / 2 for n in raw}
    span = hi - lo
    return {
        n: MIN_NODE_SIZE + (raw[n] - lo) / span * (MAX_NODE_SIZE - MIN_NODE_SIZE)
        for n in raw
    }


def _top_n_by_degree(G: nx.Graph, n: int) -> set[str]:
    if n <= 0:
        return set()
    return {node for node, _ in sorted(G.degree(), key=lambda x: -x[1])[:n]}


def _color_for_genre(genre: str) -> str:
    """Stable color per genre via hash → HSL → hex."""
    if not genre:
        return DEFAULT_COLOR
    digest = hashlib.md5(genre.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.55, 0.7)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def main() -> None:
    graphml_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"
    output_html = PROJECT_ROOT / "internal" / "data" / "collab_graph.html"
    render(graphml_path, output_html)


if __name__ == "__main__":
    main()
