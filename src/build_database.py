"""Clean the raw Steam data and load it into a SQLite database.

Creates:
    data/steam.db   - SQLite database with two tables: games and game_genres
    data/games.csv  - the games table as a CSV, for Excel or Power BI

Usage:
    python src/build_database.py
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
DETAILS_DIR = RAW_DIR / "store_details"


def load_steamspy():
    games = {}
    for path in sorted(RAW_DIR.glob("steamspy_page_*.json")):
        games.update(json.loads(path.read_text(encoding="utf-8")))
    return games


def parse_owners(owners):
    """Turn '1,000,000 .. 2,000,000' into (1000000, 2000000)."""
    low, high = owners.replace(",", "").split(" .. ")
    return int(low), int(high)


def main():
    spy = load_steamspy()
    games, genres = [], []

    for appid, g in spy.items():
        details_path = DETAILS_DIR / f"{appid}.json"
        if not details_path.exists():
            continue  # still downloading, or the download was stopped early
        details = json.loads(details_path.read_text(encoding="utf-8"))
        info = details.get("data") if details.get("success") else None
        if not info or info.get("type") != "game":
            continue  # skip DLC, software, and games removed from the store

        owners_low, owners_high = parse_owners(g["owners"])
        total_reviews = g["positive"] + g["negative"]
        games.append({
            "appid": int(appid),
            "name": g["name"],
            "developer": g["developer"],
            "publisher": g["publisher"],
            "release_date": info.get("release_date", {}).get("date"),
            "price_usd": int(g["price"] or 0) / 100,
            "full_price_usd": int(g["initialprice"] or 0) / 100,
            "discount_pct": int(g["discount"] or 0),
            "positive_reviews": g["positive"],
            "negative_reviews": g["negative"],
            "total_reviews": total_reviews,
            "positive_pct": round(100 * g["positive"] / total_reviews, 1) if total_reviews else None,
            "owners_low": owners_low,
            "owners_high": owners_high,
            "owners_mid": (owners_low + owners_high) // 2,
            "current_players": g["ccu"],
        })
        for genre in info.get("genres", []):
            genres.append({"appid": int(appid), "genre": genre["description"]})

    if not games:
        print("No game data found yet. Run python src/collect_data.py first.")
        return

    games = pd.DataFrame(games)
    # Steam writes dates a few ways ("Aug 3, 2023" or "3 Aug, 2023")
    dates = pd.to_datetime(games["release_date"], format="mixed", errors="coerce")
    games["release_date"] = dates.dt.strftime("%Y-%m-%d")
    games["release_year"] = dates.dt.year.astype("Int64")
    games["release_month"] = dates.dt.month.astype("Int64")
    genres = pd.DataFrame(genres)

    with sqlite3.connect(DATA_DIR / "steam.db") as conn:
        games.to_sql("games", conn, if_exists="replace", index=False)
        genres.to_sql("game_genres", conn, if_exists="replace", index=False)
    games.to_csv(DATA_DIR / "games.csv", index=False)

    print(f"Saved {len(games)} games and {len(genres)} genre tags to data/steam.db")


if __name__ == "__main__":
    main()
