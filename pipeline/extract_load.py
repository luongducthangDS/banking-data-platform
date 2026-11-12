"""Extract from the three sources and load into the raw layer (ELT: raw keeps source strings).

- load_files: full load of CRM CSV + lending JSON (TRUNCATE + COPY inside one transaction).
- load_transactions: incremental load of [start, end) from the core banking API;
  retries transient errors, dedupes at-least-once deliveries, ON CONFLICT DO NOTHING,
  so re-running the same interval inserts 0 rows.
Every run is logged to meta.pipeline_runs (failures too).
"""
from __future__ import annotations

import csv
import json
import logging
import os
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg
import requests

log = logging.getLogger("pipeline")
ROOT = Path(__file__).resolve().parent.parent
DSN = os.getenv("PG_DSN", "postgresql://bank:bank@localhost:5433/bank")
API = os.getenv("CORE_API_URL", "http://localhost:8001")
LANDING = Path(os.getenv("LANDING_DIR", ROOT / "landing"))

TRANS_COLS = ["trans_id", "account_id", "date", "type", "operation", "amount", "balance", "k_symbol", "bank", "account"]
FILES = {  # raw table -> (relative path, format)
    "clients": ("crm/clients.csv", "csv"), "accounts": ("crm/accounts.csv", "csv"),
    "dispositions": ("crm/dispositions.csv", "csv"), "districts": ("crm/districts.csv", "csv"),
    "standing_orders": ("crm/standing_orders.csv", "csv"),
    "loans": ("lending/loans.json", "json"), "cards": ("lending/cards.json", "json"),
}

DDL = f"""
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS meta;
CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
  run_id uuid PRIMARY KEY, task text NOT NULL, interval_start date, interval_end date,
  rows_extracted int, rows_inserted int, rows_duplicate int, status text NOT NULL,
  error text, started_at timestamptz NOT NULL, finished_at timestamptz);
CREATE TABLE IF NOT EXISTS meta.watermark (
  source text PRIMARY KEY, high_watermark date NOT NULL, updated_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS raw.transactions (
  {", ".join(f"{c} text" for c in TRANS_COLS)},
  _batch_id uuid NOT NULL, _loaded_at timestamptz NOT NULL, _source text NOT NULL,
  PRIMARY KEY (trans_id));
"""


def connect() -> psycopg.Connection:
    return psycopg.connect(DSN)


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(DDL)
    conn.commit()


def _read(path: Path, fmt: str) -> tuple[list[str], list[list[str]]]:
    if fmt == "csv":
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.reader(f, delimiter=";")
            cols = next(r)
            return [c.strip().lower() for c in cols], [row for row in r]
    data = json.loads(path.read_text(encoding="utf-8"))
    cols = list(data[0])
    return cols, [[d.get(c) for c in cols] for d in data]


def _log_run(conn, run_id, task, start, end, extracted, inserted, status, error, started):
    conn.execute(
        "INSERT INTO meta.pipeline_runs VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())",
        (run_id, task, start, end, extracted, inserted,
         None if extracted is None or inserted is None else extracted - inserted, status, error, started))
    conn.commit()


def load_files(conn: psycopg.Connection) -> dict[str, int]:
    """Full load. A failure rolls back every table, so raw never holds a half-loaded snapshot."""
    ensure_schema(conn)
    run_id, started, counts = uuid.uuid4(), datetime.now(timezone.utc), {}
    try:
        with conn.transaction():
            for table, (rel, fmt) in FILES.items():
                cols, rows = _read(LANDING / rel, fmt)
                coldefs = ", ".join(f'"{c}" text' for c in cols)
                conn.execute(f"CREATE TABLE IF NOT EXISTS raw.{table} ({coldefs}, _batch_id uuid, "
                             "_loaded_at timestamptz, _source text)")
                conn.execute(f"TRUNCATE raw.{table}")
                collist = ", ".join(f'"{c}"' for c in cols)
                with conn.cursor().copy(f"COPY raw.{table} ({collist}, _batch_id, _loaded_at, _source) FROM STDIN") as cp:
                    for row in rows:
                        cp.write_row([*row, run_id, started, rel])
                counts[table] = len(rows)
        total = sum(counts.values())
        _log_run(conn, run_id, "load_files", None, None, total, total, "success", None, started)
        log.info("load_files %s", counts)
        return counts
    except Exception as e:
        conn.rollback()
        _log_run(conn, run_id, "load_files", None, None, None, None, "failed", repr(e)[:2000], started)
        raise


SWITCH_COLS = ["switch_ref", "core_ref", "account_id", "value_date", "amount", "currency", "channel"]


def load_switch(conn: psycopg.Connection, month: str) -> int:
    """Load the payment switch settlement file for `month` (YYYY-MM). Re-loading replaces that file's rows.
    A missing file raises, so Airflow retries and the run shows the feed as late (timeliness)."""
    ensure_schema(conn)
    path = LANDING / "switch" / f"settlement_{month}.csv"
    run_id, started = uuid.uuid4(), datetime.now(timezone.utc)
    try:
        if not path.exists():
            raise FileNotFoundError(f"switch settlement file not arrived: {path.name}")
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            assert next(r) == SWITCH_COLS, f"unexpected header in {path.name}"
            rows = list(r)
        with conn.transaction():
            conn.execute(f"CREATE TABLE IF NOT EXISTS raw.switch_settlements ({', '.join(c + ' text' for c in SWITCH_COLS)}, "
                         "_file text NOT NULL, _batch_id uuid NOT NULL, _loaded_at timestamptz NOT NULL)")
            conn.execute("CREATE INDEX IF NOT EXISTS switch_settlements_file ON raw.switch_settlements (_file)")
            conn.execute("DELETE FROM raw.switch_settlements WHERE _file = %s", (path.name,))
            with conn.cursor().copy(f"COPY raw.switch_settlements ({', '.join(SWITCH_COLS)}, _file, _batch_id, _loaded_at) FROM STDIN") as cp:
                for row in rows:
                    cp.write_row([*row, path.name, run_id, started])
        _log_run(conn, run_id, "load_switch", None, None, len(rows), len(rows), "success", None, started)
        log.info("switch %s rows=%s", month, len(rows))
        return len(rows)
    except Exception as e:
        conn.rollback()
        _log_run(conn, run_id, "load_switch", None, None, None, None, "failed", repr(e)[:2000], started)
        raise


def fetch_page(start: date, end: date, page: int, retries: int = 6, session=requests) -> dict:
    """GET one page; retry 5xx/connection errors with exponential backoff, fail fast on 4xx."""
    for attempt in range(retries):
        try:
            r = session.get(f"{API}/transactions", timeout=60, params={
                "date_from": start.isoformat(), "date_to": end.isoformat(), "page": page, "page_size": 5000})
            if r.status_code < 500:
                r.raise_for_status()
                return r.json()
            err = f"HTTP {r.status_code}"
        except requests.ConnectionError as e:
            err = repr(e)
        wait = min(2 ** attempt * 0.5, 30)
        log.warning("page %s attempt %s failed (%s), retry in %.1fs", page, attempt + 1, err, wait)
        time.sleep(wait)
    raise RuntimeError(f"core API failed after {retries} attempts: {err}")


def load_transactions(conn: psycopg.Connection, start: date, end: date) -> dict[str, int]:
    """Incremental load of [start, end). Idempotent: re-running inserts nothing new."""
    ensure_schema(conn)
    run_id, started = uuid.uuid4(), datetime.now(timezone.utc)
    try:
        rows, page, pages = [], 1, 1
        while page <= pages:
            body = fetch_page(start, end, page)
            pages = body["total_pages"]
            rows += body["data"]
            page += 1
        with conn.transaction():
            conn.execute("CREATE TEMP TABLE t_in (LIKE raw.transactions INCLUDING DEFAULTS) ON COMMIT DROP")
            with conn.cursor().copy(f"COPY t_in ({', '.join(TRANS_COLS)}, _batch_id, _loaded_at, _source) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row([r[c] for c in TRANS_COLS] + [run_id, started, "core-api"])
            inserted = conn.execute(
                "INSERT INTO raw.transactions SELECT DISTINCT ON (trans_id) * FROM t_in "
                "ORDER BY trans_id ON CONFLICT (trans_id) DO NOTHING").rowcount
            conn.execute(
                "INSERT INTO meta.watermark VALUES ('core-api.transactions', %s, now()) "
                "ON CONFLICT (source) DO UPDATE SET high_watermark = GREATEST(meta.watermark.high_watermark, "
                "EXCLUDED.high_watermark), updated_at = now()", (end,))
        _log_run(conn, run_id, "load_transactions", start, end, len(rows), inserted, "success", None, started)
        log.info("transactions %s..%s extracted=%s inserted=%s", start, end, len(rows), inserted)
        return {"extracted": len(rows), "inserted": inserted}
    except Exception as e:
        conn.rollback()
        _log_run(conn, run_id, "load_transactions", start, end, None, None, "failed", repr(e)[:2000], started)
        raise
