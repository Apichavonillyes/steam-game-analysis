"""Export the games data for the web dashboard.

Creates docs/data.js, which docs/index.html loads. Run this after
build_database.py whenever the data changes.

Usage:
    python src/export_dashboard_data.py
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "steam.db"
OUT_PATH = ROOT / "docs" / "data.js"

# Each game becomes a short list instead of an object to keep the file small.
# The dashboard reads the columns in this order.
COLUMNS = [
    "appid", "name", "developer", "full_price_usd", "positive_pct",
    "total_reviews", "owners_low", "owners_high", "release_date",
    "current_players", "genres",
]


def main():
    with sqlite3.connect(DB_PATH) as conn:
        games = pd.read_sql_query("SELECT * FROM games", conn)
        genres = pd.read_sql_query("SELECT * FROM game_genres", conn)

    genre_lists = genres.groupby("appid")["genre"].apply(list)
    games["genres"] = games["appid"].map(genre_lists).apply(lambda g: g if isinstance(g, list) else [])
    games = games.astype(object).where(games.notna(), None)

    rows = games[COLUMNS].values.tolist()
    data = {"columns": COLUMNS, "rows": rows, "collected": "September 2026"}

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        "// Made by src/export_dashboard_data.py. Don't edit by hand.\n"
        f"window.STEAM_DATA = {json.dumps(data, separators=(',', ':'), ensure_ascii=False)};\n",
        encoding="utf-8",
    )
    print(f"Saved {len(rows)} games to docs/data.js ({OUT_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
