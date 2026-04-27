"""Plot the component-size distribution of ``collab_graph.graphml``.

Covers partial-submission requirement (5): for each component size k,
how many connected components of the graph have exactly k vertices.

Run from the project root: ``python -m internal.metrics.component_sizes``
                     or:  ``python internal/metrics/component_sizes.py``
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def component_size_distribution(G: nx.Graph) -> Counter[int]:
    return Counter(len(c) for c in nx.connected_components(G))


def plot_component_sizes(G: nx.Graph, output_path: Path) -> None:
    dist = component_size_distribution(G)
    sizes = sorted(dist)
    counts = [dist[k] for k in sizes]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(
        [str(s) for s in sizes],
        counts,
        color="steelblue",
        edgecolor="black",
        linewidth=0.5,
    )
    ax.set_xlabel("Tamanho da componente (k)")
    ax.set_ylabel("Número de componentes com k vértices")
    ax.set_title("Distribuição de tamanhos das componentes — grafo de colaborações")
    # Component sizes range from 1 to thousands; log-y keeps the giant
    # component and the singletons readable in the same plot.
    ax.set_yscale("log")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    for x, c in zip([str(s) for s in sizes], counts):
        ax.text(x, c, str(c), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    graphml_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"
    output_path = PROJECT_ROOT / "internal" / "data" / "component_sizes.png"

    G = nx.read_graphml(graphml_path)
    print(f"Loaded {graphml_path.name}: |V|={G.number_of_nodes()}, |E|={G.number_of_edges()}")

    dist = component_size_distribution(G)
    print("\nComponent size histogram (size: how many components have that size):")
    for k in sorted(dist):
        print(f"  {k:>5}: {dist[k]}")

    plot_component_sizes(G, output_path)
    print(f"\nSaved plot to {output_path}")


if __name__ == "__main__":
    main()
