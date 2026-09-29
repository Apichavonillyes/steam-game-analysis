"""Make one chart for each question and save them to charts/.

Usage:
    python src/make_charts.py
"""
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "steam.db"
CHART_DIR = ROOT / "charts"

BLUE = "#2a78d6"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"
MIN_REVIEWS = 500  # same filter as sql/analysis.sql

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 11,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": TEXT_SECONDARY,
    "axes.titlecolor": TEXT,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": TEXT_SECONDARY,
    "ytick.labelcolor": TEXT_SECONDARY,
})


def query(conn, sql):
    return pd.read_sql_query(sql, conn)


def finish(fig, ax, title, subtitle, filename):
    ax.set_title(title, pad=28)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=TEXT_SECONDARY, fontsize=10)
    fig.tight_layout()
    fig.savefig(CHART_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"Saved charts/{filename}")


def price_vs_reviews(conn):
    df = query(conn, f"""
        SELECT
            CASE
                WHEN full_price_usd = 0 THEN 'Free'
                WHEN full_price_usd < 10 THEN 'Under $10'
                WHEN full_price_usd < 20 THEN '$10-19'
                WHEN full_price_usd < 40 THEN '$20-39'
                ELSE '$40+'
            END AS price_range,
            MIN(full_price_usd) AS sort_key,
            COUNT(*) AS games,
            AVG(positive_pct) AS avg_positive_pct
        FROM games
        WHERE total_reviews >= {MIN_REVIEWS}
        GROUP BY price_range
        ORDER BY sort_key
    """)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(df["price_range"], df["avg_positive_pct"], width=0.6, color=BLUE)
    ax.bar_label(bars, labels=[f"{v:.0f}%" for v in df["avg_positive_pct"]],
                 padding=4, color=TEXT, fontweight="bold")
    ax.set_xticks(range(len(df)), [f"{p}\n{n} games" for p, n in zip(df["price_range"], df["games"])])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Average positive reviews (%)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    finish(fig, ax, "Do cheaper games get better reviews?",
           f"Average share of positive reviews by full price, games with {MIN_REVIEWS}+ reviews",
           "1_price_vs_reviews.png")


def genre_reviews(conn):
    df = query(conn, f"""
        SELECT gg.genre, COUNT(*) AS games, AVG(g.positive_pct) AS avg_positive_pct
        FROM game_genres gg
        JOIN games g ON g.appid = gg.appid
        WHERE g.total_reviews >= {MIN_REVIEWS}
        GROUP BY gg.genre
        HAVING COUNT(*) >= 20
        ORDER BY avg_positive_pct
    """)
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(df) + 1.6))
    bars = ax.barh(df["genre"], df["avg_positive_pct"], height=0.6, color=BLUE)
    ax.bar_label(bars, labels=[f"{v:.0f}%  ({n} games)" for v, n in zip(df["avg_positive_pct"], df["games"])],
                 padding=4, color=TEXT_SECONDARY, fontsize=10)
    ax.set_xlim(0, 115)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Average positive reviews (%)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    finish(fig, ax, "Which genres get the best reviews?",
           f"Genres with 20+ games, games with {MIN_REVIEWS}+ reviews. A game can have several genres.",
           "2_genre_reviews.png")


def genre_growth(conn):
    genres = ["Action", "Adventure", "RPG", "Strategy", "Simulation", "Indie"]
    df = query(conn, f"""
        SELECT g.release_year, gg.genre, COUNT(*) AS games
        FROM game_genres gg
        JOIN games g ON g.appid = gg.appid
        WHERE g.release_year BETWEEN 2015 AND 2025
          AND gg.genre IN ({", ".join(f"'{x}'" for x in genres)})
        GROUP BY g.release_year, gg.genre
    """)
    years = range(2015, 2026)
    table = df.pivot(index="release_year", columns="genre", values="games").reindex(years).fillna(0)

    # Small multiples: one panel per genre, same y-axis, so they're easy to compare
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.5), sharex=True, sharey=True)
    for ax, genre in zip(axes.flat, genres):
        values = table[genre] if genre in table else pd.Series(0, index=years)
        ax.plot(values.index, values, color=BLUE, linewidth=2)
        ax.plot(values.index[-1], values.iloc[-1], "o", color=BLUE, markersize=6)
        ax.set_title(genre, fontsize=11, pad=6)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xticks([2015, 2020, 2025])
        ax.yaxis.get_major_locator().set_params(integer=True)
        ax.set_ylim(bottom=0)
    fig.suptitle("Which genres are growing?", x=0.01, ha="left", fontsize=14, fontweight="bold", color=TEXT)
    fig.text(0.01, 0.905, "Top games released each year, by genre (2015-2025)", color=TEXT_SECONDARY, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(CHART_DIR / "3_genre_growth.png", dpi=150)
    plt.close(fig)
    print("Saved charts/3_genre_growth.png")


def launch_month(conn):
    df = query(conn, """
        SELECT release_month, COUNT(*) AS games, AVG(owners_mid) / 1000000.0 AS avg_owners_millions
        FROM games
        WHERE release_month IS NOT NULL
        GROUP BY release_month
        ORDER BY release_month
    """)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    df = df.set_index("release_month").reindex(range(1, 13))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(months, df["avg_owners_millions"].fillna(0), width=0.6, color=BLUE)
    ax.bar_label(bars, labels=[f"{v:.1f}M" if pd.notna(v) else "" for v in df["avg_owners_millions"]],
                 padding=4, color=TEXT_SECONDARY, fontsize=9)
    ax.set_xticks(range(12), [f"{m}\n{int(n) if pd.notna(n) else 0}" for m, n in zip(months, df["games"])])
    ax.set_ylim(0, df["avg_owners_millions"].max() * 1.15)
    ax.set_ylabel("Average owners (millions)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    finish(fig, ax, "Is there a best month to launch a game?",
           "Average estimated owners by release month. Number under each month = games released.",
           "4_launch_month.png")


def main():
    CHART_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        price_vs_reviews(conn)
        genre_reviews(conn)
        genre_growth(conn)
        launch_month(conn)


if __name__ == "__main__":
    main()
