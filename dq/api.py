"""Read-only API over DQ and reconciliation results (connects as analyst_ro).

  uvicorn dq.api:app --port 8002
"""
import os
from datetime import date

import psycopg
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

DSN = os.getenv("RO_DSN", "postgresql://analyst_ro:analyst_ro@localhost:5433/bank")
app = FastAPI(title="Banking DQ & Reconciliation API")


def rows(sql: str, params: tuple = ()) -> list[dict]:
    try:
        with psycopg.connect(DSN, row_factory=dict_row) as conn:
            return conn.execute(sql, params).fetchall()
    except psycopg.errors.UndefinedTable:
        raise HTTPException(503, "DQ has not run yet")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dq/summary")
def summary():
    """Per rule over all intervals: how many months failed and total violations."""
    return rows("""select rule_id, dimension, description, count(*) as intervals,
                          count(*) filter (where not success) as failed_intervals,
                          sum(unexpected_count)::int as violations, max(interval_start) as latest_interval
                   from dq.check_results group by 1, 2, 3 order by dimension, rule_id""")


@app.get("/dq/results")
def results(interval_start: date):
    """All rule results for one month (interval_start = first day of the month)."""
    out = rows("select * from dq.check_results where interval_start = %s order by dimension, rule_id", (interval_start,))
    if not out:
        raise HTTPException(404, f"no results for {interval_start}")
    return out


@app.get("/dq/errors")
def errors(rule_id: str, interval_start: date | None = None, limit: int = Query(100, le=1000)):
    """Offending records for a rule (capped at 1000 per rule and month at write time)."""
    if interval_start:
        return rows("""select interval_start, record_key, record from dq.error_records
                       where rule_id = %s and interval_start = %s limit %s""", (rule_id, interval_start, limit))
    return rows("""select interval_start, record_key, record from dq.error_records
                   where rule_id = %s order by interval_start limit %s""", (rule_id, limit))


@app.get("/recon/summary")
def recon_summary(interval_start: date | None = None):
    """Break counts by type, for one month or overall."""
    if interval_start:
        return rows("""select break_type, count(*) as breaks from recon.breaks
                       where interval_start = %s group by 1 order by 2 desc""", (interval_start,))
    return rows("select break_type, count(*) as breaks from recon.breaks group by 1 order by 2 desc")


@app.get("/recon/breaks")
def recon_breaks(break_type: str, interval_start: date | None = None, limit: int = Query(100, le=1000)):
    sql = "select * from recon.breaks where break_type = %s"
    params: tuple = (break_type,)
    if interval_start:
        sql, params = sql + " and interval_start = %s", (*params, interval_start)
    return rows(sql + " order by interval_start, switch_ref limit %s", (*params, limit))
