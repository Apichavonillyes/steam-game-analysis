"""Run every query in a .sql file against data/steam.db and print the results.

Usage:
    python src/run_sql.py sql/analysis.sql
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "steam.db"

sql = Path(sys.argv[1]).read_text(encoding="utf-8")
with sqlite3.connect(DB_PATH) as conn:
    for query in sql.split(";"):
        # keep the comment lines so each result has its question as a title
        title = [line for line in query.strip().splitlines() if line.startswith("--")]
        body = [line for line in query.strip().splitlines() if not line.startswith("--")]
        if not "".join(body).strip():
            continue
        print("\n".join(title))
        print(pd.read_sql_query(query, conn).to_string(index=False))
        print()
