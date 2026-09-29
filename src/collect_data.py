"""Collect Steam game data from SteamSpy and the Steam store API.

Step 1: SteamSpy gives owners, reviews, price and player counts for the
most-owned games on Steam (1,000 games per page).
Step 2: The Steam store API adds the release date and genres for each game.

Every response is saved in data/raw/, so you can stop the script and run it
again later. It picks up where it left off.

Usage:
    python src/collect_data.py            # top 2,000 games (about 55 minutes)
    python src/collect_data.py --pages 1  # top 1,000 games
"""
import argparse
import json
import time
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DETAILS_DIR = RAW_DIR / "store_details"

STEAMSPY_URL = "https://steamspy.com/api.php"
STORE_URL = "https://store.steampowered.com/api/appdetails"

STEAMSPY_WAIT = 60  # SteamSpy allows one "all" request per minute
STORE_WAIT = 1.5    # the store allows about 200 requests every 5 minutes


def get_json(url, params):
    """GET a URL and return its JSON, waiting and retrying if rate limited
    or if the connection drops."""
    for _ in range(5):
        try:
            resp = requests.get(url, params=params, timeout=30)
        except (requests.ConnectionError, requests.Timeout):
            print("  Connection problem, waiting 30 seconds...")
            time.sleep(30)
            continue
        if resp.status_code in (403, 429):
            print("  Rate limited, waiting 60 seconds...")
            time.sleep(60)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Gave up after 5 tries: {url} {params}")


def collect_steamspy(pages):
    """Download the SteamSpy game list and return {appid: game}."""
    games = {}
    made_request = False
    for page in range(pages):
        path = RAW_DIR / f"steamspy_page_{page}.json"
        if not path.exists():
            if made_request:
                time.sleep(STEAMSPY_WAIT)
            print(f"Downloading SteamSpy page {page}...")
            data = get_json(STEAMSPY_URL, {"request": "all", "page": page})
            path.write_text(json.dumps(data), encoding="utf-8")
            made_request = True
        games.update(json.loads(path.read_text(encoding="utf-8")))
    return games


def collect_store_details(appids):
    """Download release date and genres for each game from the Steam store."""
    todo = [a for a in appids if not (DETAILS_DIR / f"{a}.json").exists()]
    print(f"{len(appids) - len(todo)} games already saved, {len(todo)} to go.")

    for i, appid in enumerate(todo, start=1):
        data = get_json(STORE_URL, {
            "appids": appid,
            "cc": "us",
            "filters": "basic,genres,release_date,price_overview",
        })
        details = (data or {}).get(str(appid), {})
        (DETAILS_DIR / f"{appid}.json").write_text(json.dumps(details), encoding="utf-8")

        if i % 100 == 0:
            print(f"  {i} / {len(todo)} done")
        time.sleep(STORE_WAIT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=2,
                        help="pages of 1,000 games to download from SteamSpy")
    args = parser.parse_args()

    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    games = collect_steamspy(args.pages)
    print(f"Got {len(games)} games from SteamSpy.")
    collect_store_details(list(games))
    print("Done! Next run: python src/build_database.py")


if __name__ == "__main__":
    main()
