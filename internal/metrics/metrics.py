"""Compute and print structural metrics for ``collab_graph.graphml``.

Covers the partial-submission requirements:
- (2) graph size: |V|, |E|, average degree
- (4) number of connected components (undirected graph)
- (5) size distribution of those components

Run from the project root: ``python -m internal.metrics.metrics``
                     or:  ``python internal/metrics/metrics.py``
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SMALL_COMPONENT_THRESHOLD = 5


def compute(G: nx.Graph) -> dict[str, object]:
    n = G.number_of_nodes()
    m = G.number_of_edges()
    # In an undirected simple graph, sum(degrees) = 2m, so avg_degree = 2m/n.
    avg_degree = (2 * m / n) if n > 0 else 0.0

    components = [set(c) for c in nx.connected_components(G)]
    component_sizes = sorted((len(c) for c in components), reverse=True)

    small = [c for c in components if len(c) <= SMALL_COMPONENT_THRESHOLD]
    # Pretty-print order: smallest groups first; alphabetical within a group.
    small.sort(key=lambda c: (len(c), sorted(_node_name(G, n) for n in c)))
    small_components = [
        sorted(_node_name(G, node) for node in component) for component in small
    ]

    return {
        "vertices": n,
        "edges": m,
        "average_degree": avg_degree,
        "connected_components": len(component_sizes),
        "component_sizes": component_sizes,
        "small_components": small_components,
    }


def _node_name(G: nx.Graph, node: str) -> str:
    return G.nodes[node].get("name") or node


def print_report(metrics: dict[str, object]) -> None:
    print(f"Vertices            (|V|): {metrics['vertices']}")
    print(f"Edges               (|E|): {metrics['edges']}")
    print(f"Average degree (2|E|/|V|): {metrics['average_degree']:.4f}")
    print(f"Connected components     : {metrics['connected_components']}")

    sizes: list[int] = metrics["component_sizes"]  # type: ignore[assignment]
    if not sizes:
        return

    print("\nComponent sizes (largest first):")
    for i, size in enumerate(sizes, 1):
        print(f"  #{i:>4}: {size} vertices")

    # Histogram-style summary: how many components have exactly k vertices.
    print("\nSize histogram (size: how many components have that size):")
    for size, count in sorted(Counter(sizes).items()):
        print(f"  {size:>5}: {count}")

    small: list[list[str]] = metrics["small_components"]  # type: ignore[assignment]
    if small:
        print(
            f"\nArtists in small components "
            f"(size <= {SMALL_COMPONENT_THRESHOLD}):"
        )
        for component in small:
            print(f"  [{len(component)}] {', '.join(component)}")


def main() -> None:
    graphml_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"
    G = nx.read_graphml(graphml_path)
    print(f"Loaded {graphml_path.name}\n")
    print_report(compute(G))


if __name__ == "__main__":
    main()
