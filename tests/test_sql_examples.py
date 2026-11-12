"""Every interview SQL file must run against the warehouse (inside a rolled-back transaction)."""
from pathlib import Path

import psycopg
import pytest

SQL_DIR = Path(__file__).resolve().parent.parent / "analytics" / "sql"


@pytest.mark.parametrize("path", sorted(SQL_DIR.glob("*.sql")), ids=lambda p: p.name)
def test_sql_file_runs(conn, path):
    try:
        with conn.transaction(force_rollback=True):
            cur = conn.execute(path.read_text(encoding="utf-8"))
            while cur.nextset():  # multi-statement files: check the last result
                pass
            rows = cur.fetchall()
    except psycopg.errors.UndefinedTable:
        pytest.skip("warehouse not built (dbt build)")
    assert rows, f"{path.name} returned no rows"
