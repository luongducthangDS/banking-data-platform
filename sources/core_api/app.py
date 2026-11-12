"""Simulated core banking REST API serving the Berka transactions.

Real behaviour it imitates (rates set by env, see .env.example):
- transient failures: a request fails with 503 at CORE_API_FAIL_RATE;
- at-least-once delivery: CORE_API_DUP_RATE of rows on a page are sent twice.
Records are returned exactly as the source stores them (YYMMDD dates, Czech codes, strings).
"""
import os
import random
from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

DATA = Path(os.getenv("TRANS_FILE") or Path(__file__).resolve().parents[2] / "data" / "raw" / "trans.asc")
FAIL_RATE = float(os.getenv("CORE_API_FAIL_RATE", "0"))
DUP_RATE = float(os.getenv("CORE_API_DUP_RATE", "0"))

app = FastAPI(title="core-banking (simulated)")
_df: pd.DataFrame | None = None


def trans() -> pd.DataFrame:
    global _df
    if _df is None:
        df = pd.read_csv(DATA, sep=";", dtype=str, keep_default_na=False)
        df["_d"] = pd.to_datetime("19" + df["date"], format="%Y%m%d")
        _df = df.sort_values(["_d", "trans_id"]).reset_index(drop=True)
    return _df


@app.get("/health")
def health():
    return {"status": "ok", "rows": len(trans())}


@app.get("/transactions")
def transactions(date_from: date, date_to: date, page: int = Query(1, ge=1),
                 page_size: int = Query(5000, ge=1, le=20000)):
    """Transactions with date_from <= date < date_to, ordered by (date, trans_id)."""
    if random.random() < FAIL_RATE:
        raise HTTPException(503, "core banking temporarily unavailable")
    df = trans()
    sel = df[(df["_d"] >= pd.Timestamp(date_from)) & (df["_d"] < pd.Timestamp(date_to))]
    total_pages = max(1, -(-len(sel) // page_size))
    rows = sel.iloc[(page - 1) * page_size: page * page_size].drop(columns="_d").to_dict("records")
    rows += [r for r in rows if random.random() < DUP_RATE]
    return {"data": rows, "page": page, "page_size": page_size, "total_rows": len(sel), "total_pages": total_pages}
