"""Plot the degree distribution of ``collab_graph.graphml``.

Covers partial-submission requirement (3): a visual representation of the
degree distribution — for each degree k, how many vertices have that degree.

Run from the project root: ``python -m internal.metrics.node_degrees``
                     or:  ``python internal/metrics/node_degrees.py``
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


def degree_distribution(G: nx.Graph) -> Counter[int]:
    return Counter(deg for _, deg in G.degree())


def plot_degree_distribution(
    G: nx.Graph, output_path: Path, *, log_scale: bool = True
) -> None:
    degrees = [deg for _, deg in G.degree()]
    max_degree = max(degrees) if degrees else 0
    bin_width = 10
    bins = range(0, max_degree + bin_width + 1, bin_width)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(degrees, bins=bins, color="steelblue", edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Grau (k)")
    ax.set_ylabel("Número de vértices")
    ax.set_title("Histograma de graus — grafo de colaborações")
    if log_scale:
        # Degree distributions in collaboration networks are typically heavy-tailed;
        # log-y makes both the bulk and the long tail readable in one plot.
        ax.set_yscale("log")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    graphml_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"
    output_path = PROJECT_ROOT / "internal" / "data" / "degree_distribution.png"

    G = nx.read_graphml(graphml_path)
    print(f"Loaded {graphml_path.name}: |V|={G.number_of_nodes()}, |E|={G.number_of_edges()}")

    dist = degree_distribution(G)
    print("\nDegree histogram (degree: how many vertices have that degree):")
    for k in sorted(dist):
        print(f"  {k:>5}: {dist[k]}")

    plot_degree_distribution(G, output_path)
    print(f"\nSaved plot to {output_path}")


if __name__ == "__main__":
    main()
