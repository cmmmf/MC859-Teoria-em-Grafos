"""Genre diversity analysis for the collaboration graph.

For each of the 96 seed artists found in the graph:
  - Computes Shannon entropy H over genres of neighbours (edge weight >= MIN_WEIGHT),
    weighted by the number of collaborations
  - Computes normalised betweenness centrality (Brandes algorithm via NetworkX)
  - Uses monthly_listeners from top100artists.py as the popularity metric

Statistical analysis:
  1. Exploratory: distributions of H, betweenness, and popularity
  2. Spearman correlations between all three pairs
  3. Mann-Whitney U (bottom vs top quartile of H) + rank-biserial effect size
  4. OLS regression: log(popularity) ~ H + betweenness + genre dummies

Run from the project root:
    python -m internal.analysis.genre_diversity
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from internal.data.top100artists import TOP_100_ARTISTS
from internal.services.graph_builder import _load_genre_cache

MIN_WEIGHT = 2
FIGURES_DIR = PROJECT_ROOT / "internal" / "data"


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_enriched_graph() -> nx.Graph:
    """Load the GraphML and apply all known genres from the CSV cache."""
    graphml_path = PROJECT_ROOT / "internal" / "data" / "collab_graph.graphml"
    cache_path = PROJECT_ROOT / "internal" / "data" / "artist_genres.csv"

    G = nx.read_graphml(graphml_path)
    genre_cache = _load_genre_cache(cache_path)
    for node in G.nodes():
        if not G.nodes[node].get("main_genre") and node in genre_cache:
            G.nodes[node]["main_genre"] = genre_cache[node]
    return G


# ---------------------------------------------------------------------------
# Seed identification
# ---------------------------------------------------------------------------

def identify_seeds(G: nx.Graph) -> dict[str, dict]:
    """Return {mbid: artist_dict} for seeds present in the graph."""
    name_to_artist = {a["name"]: a for a in TOP_100_ARTISTS}
    seeds: dict[str, dict] = {}
    for node, data in G.nodes(data=True):
        name = data.get("name", "")
        if name in name_to_artist:
            seeds[node] = name_to_artist[name]
    return seeds


# ---------------------------------------------------------------------------
# Shannon entropy (weighted by edge weight)
# ---------------------------------------------------------------------------

def shannon_entropy(G: nx.Graph, node: str) -> float | None:
    """Weighted Shannon entropy over neighbour genres (edge weight >= MIN_WEIGHT).

    Uses edge weight as the number of collaborations with each neighbour.
    Neighbours with no genre are excluded. Returns None if no valid neighbours.
    """
    genre_weight: dict[str, float] = {}
    for nb, edata in G[node].items():
        weight = edata.get("weight") or 1
        if weight < MIN_WEIGHT:
            continue
        genre = G.nodes[nb].get("main_genre") or ""
        if not genre:
            continue
        genre_weight[genre] = genre_weight.get(genre, 0.0) + weight

    total = sum(genre_weight.values())
    if total == 0:
        return None

    return -sum((w / total) * math.log2(w / total) for w in genre_weight.values())


# ---------------------------------------------------------------------------
# Build dataframe
# ---------------------------------------------------------------------------

def build_dataframe(G: nx.Graph, seeds: dict[str, dict]) -> pd.DataFrame:
    """Compute all per-seed metrics and return as a DataFrame."""
    print("Computing betweenness centrality (Brandes)...")
    bc = nx.betweenness_centrality(G, normalized=True)
    print("Done.")

    rows = []
    for mbid, artist in seeds.items():
        H = shannon_entropy(G, mbid)
        if H is None:
            continue
        rows.append({
            "mbid": mbid,
            "name": artist["name"],
            "monthly_listeners": artist["monthly_listeners"],
            "H": H,
            "betweenness": bc[mbid],
            "main_genre": G.nodes[mbid].get("main_genre") or "unknown",
            "degree": G.degree(mbid),
        })

    df = pd.DataFrame(rows)
    df["log_listeners"] = np.log10(df["monthly_listeners"])
    return df


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def run_correlations(df: pd.DataFrame) -> None:
    print("\n=== Spearman Correlations ===")
    pairs = [
        ("H", "log_listeners", "H vs log(monthly listeners)"),
        ("betweenness", "log_listeners", "betweenness vs log(monthly listeners)"),
        ("H", "betweenness", "H vs betweenness"),
    ]
    for x, y, label in pairs:
        rho, p = stats.spearmanr(df[x], df[y])
        print(f"  {label}: rho={rho:+.3f}, p={p:.4f}")


def run_mannwhitney(df: pd.DataFrame) -> None:
    print("\n=== Mann-Whitney U: bottom vs top quartile of H ===")
    q1 = df["H"].quantile(0.25)
    q3 = df["H"].quantile(0.75)
    low = df[df["H"] <= q1]["log_listeners"]
    high = df[df["H"] >= q3]["log_listeners"]
    print(f"  Low-H  group (H <= {q1:.3f}): n={len(low)}")
    print(f"  High-H group (H >= {q3:.3f}): n={len(high)}")

    u_stat, p = stats.mannwhitneyu(low, high, alternative="two-sided")
    # Rank-biserial: positive = high-H tends to have higher listeners
    r = 1 - (2 * u_stat) / (len(low) * len(high))
    print(f"  U={u_stat:.1f}, p={p:.4f}, rank-biserial r={r:+.3f}")


def run_regression(df: pd.DataFrame) -> None:
    print("\n=== OLS Regression: log(listeners) ~ H + betweenness + genre ===")

    # One-hot encode genre, drop most frequent as reference
    genre_dummies = pd.get_dummies(df["main_genre"], prefix="genre", drop_first=True)
    X = pd.concat([
        pd.Series(np.ones(len(df)), name="intercept"),
        df[["H", "betweenness"]],
        genre_dummies,
    ], axis=1).values.astype(float)
    y = df["log_listeners"].values

    coef, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ coef
    n, k = X.shape
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot

    sigma2 = ss_res / (n - k)
    cov = sigma2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t_stats = coef / se
    p_values = 2 * stats.t.sf(np.abs(t_stats), df=n - k)

    col_names = ["intercept", "H", "betweenness"] + list(genre_dummies.columns)
    print(f"  R² = {r2:.3f}  (n={n}, k={k})")
    print(f"  {'Variable':<30} {'coef':>8} {'se':>8} {'t':>7} {'p':>7}")
    for name, c, s, t, p in zip(col_names, coef, se, t_stats, p_values):
        sig = "*" if p < 0.05 else ""
        print(f"  {name:<30} {c:>8.4f} {s:>8.4f} {t:>7.2f} {p:>7.4f} {sig}")


# ---------------------------------------------------------------------------
# Visualisations
# ---------------------------------------------------------------------------

def plot_distributions(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    axes[0].hist(df["H"], bins=20, edgecolor="black")
    axes[0].set_title("Distribuição de H (entropia de gênero)")
    axes[0].set_xlabel("H (bits)")
    axes[0].set_ylabel("Frequência")

    axes[1].hist(df["log_listeners"], bins=20, edgecolor="black")
    axes[1].set_title("Distribuição de log₁₀(monthly listeners)")
    axes[1].set_xlabel("log₁₀(listeners)")

    axes[2].hist(df["betweenness"], bins=20, edgecolor="black")
    axes[2].set_title("Distribuição de betweenness centrality")
    axes[2].set_xlabel("Betweenness (normalizado)")

    plt.tight_layout()
    path = FIGURES_DIR / "analysis_distributions.png"
    plt.savefig(path, dpi=150)
    print(f"\nSalvo: {path}")
    plt.close()


def plot_scatter_h_vs_popularity(df: pd.DataFrame) -> None:
    genres = df["main_genre"].unique()
    cmap = plt.get_cmap("tab20")
    color_map = {g: cmap(i / len(genres)) for i, g in enumerate(genres)}

    fig, ax = plt.subplots(figsize=(11, 7))
    for genre, group in df.groupby("main_genre"):
        ax.scatter(group["H"], group["log_listeners"],
                   label=genre, color=color_map[genre], alpha=0.8, s=60)

    # Spearman trend line via rank regression
    rho, p = stats.spearmanr(df["H"], df["log_listeners"])
    m, b = np.polyfit(df["H"], df["log_listeners"], 1)
    x_line = np.linspace(df["H"].min(), df["H"].max(), 100)
    ax.plot(x_line, m * x_line + b, "k--", linewidth=1,
            label=f"tendência (ρ={rho:+.2f}, p={p:.3f})")

    # 8 artists to label: highest/lowest listeners + 6 spread across the plot
    to_label = {
        "Taylor Swift",    # highest monthly listeners
        "Porter Robinson", # lowest monthly listeners
        "Elton John",      # highest H
        "Gorillaz",        # second highest H
        "Eminem",          # low H, very high listeners
        "Billie Eilish",   # very low H, high listeners
        "Ariana Grande",   # high listeners, high H
        "Lil Wayne",       # low H, highest degree in graph
    }
    # offsets: (dx, dy) in data units to avoid overlap
    label_offsets = {
        "Taylor Swift":    ( 0.05,  0.04),
        "Porter Robinson": ( 0.05, -0.05),
        "Elton John":      ( 0.05,  0.03),
        "Gorillaz":        (-0.60, -0.05),
        "Eminem":          ( 0.05,  0.03),
        "Billie Eilish":   ( 0.05, -0.05),
        "Ariana Grande":   ( 0.05,  0.03),
        "Lil Wayne":       ( 0.05,  0.03),
    }
    for _, row in df[df["name"].isin(to_label)].iterrows():
        dx, dy = label_offsets.get(row["name"], (0.05, 0.03))
        ax.annotate(
            row["name"],
            xy=(row["H"], row["log_listeners"]),
            xytext=(row["H"] + dx, row["log_listeners"] + dy),
            fontsize=7.5,
            arrowprops=dict(arrowstyle="-", color="black", lw=0.6),
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="none"),
        )

    ax.set_xlabel("H — entropia de diversidade de gênero (bits)")
    ax.set_ylabel("log₁₀(monthly listeners)")
    ax.set_title("Diversidade de colaborações vs. popularidade")
    ax.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    path = FIGURES_DIR / "analysis_h_vs_popularity.png"
    plt.savefig(path, dpi=150)
    print(f"Salvo: {path}")
    plt.close()


def plot_scatter_h_vs_betweenness(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    genres = df["main_genre"].unique()
    cmap = plt.get_cmap("tab20")
    color_map = {g: cmap(i / len(genres)) for i, g in enumerate(genres)}

    for genre, group in df.groupby("main_genre"):
        ax.scatter(group["H"], group["betweenness"],
                   label=genre, color=color_map[genre], alpha=0.8, s=60)

    rho, p = stats.spearmanr(df["H"], df["betweenness"])
    m, b = np.polyfit(df["H"], df["betweenness"], 1)
    x_line = np.linspace(df["H"].min(), df["H"].max(), 100)
    ax.plot(x_line, m * x_line + b, "k--", linewidth=1,
            label=f"tendência (ρ={rho:+.2f}, p={p:.3f})")

    ax.set_xlabel("H — entropia de diversidade de gênero (bits)")
    ax.set_ylabel("Betweenness centrality (normalizado)")
    ax.set_title("Diversidade de colaborações vs. centralidade de intermediação")
    ax.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    path = FIGURES_DIR / "analysis_h_vs_betweenness.png"
    plt.savefig(path, dpi=150)
    print(f"Salvo: {path}")
    plt.close()


def plot_boxplot_quartiles(df: pd.DataFrame) -> None:
    q1 = df["H"].quantile(0.25)
    q3 = df["H"].quantile(0.75)
    low = df[df["H"] <= q1]["log_listeners"]
    high = df[df["H"] >= q3]["log_listeners"]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot([low, high], labels=[f"Baixa diversidade\n(H ≤ {q1:.2f})", f"Alta diversidade\n(H ≥ {q3:.2f})"])
    ax.set_ylabel("log₁₀(monthly listeners)")
    ax.set_title("Popularidade por grupo de diversidade de gênero")
    plt.tight_layout()
    path = FIGURES_DIR / "analysis_boxplot_quartiles.png"
    plt.savefig(path, dpi=150)
    print(f"Salvo: {path}")
    plt.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    G = load_enriched_graph()
    seeds = identify_seeds(G)
    print(f"Seeds encontrados no grafo: {len(seeds)}")

    df = build_dataframe(G, seeds)
    print(f"Seeds com H calculável: {len(df)}")
    print(df[["name", "H", "betweenness", "log_listeners", "main_genre"]].to_string(index=False))

    run_correlations(df)
    run_mannwhitney(df)
    run_regression(df)

    plot_distributions(df)
    plot_scatter_h_vs_popularity(df)
    plot_scatter_h_vs_betweenness(df)
    plot_boxplot_quartiles(df)

    csv_out = FIGURES_DIR / "analysis_results.csv"
    df.to_csv(csv_out, index=False)
    print(f"\nDados exportados: {csv_out}")


if __name__ == "__main__":
    main()
