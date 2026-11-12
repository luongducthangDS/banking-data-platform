import sys
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.extract_load import DSN  # noqa: E402


@pytest.fixture(scope="session")
def conn():
    """Live warehouse connection; tests that need it skip when Postgres is not up."""
    try:
        c = psycopg.connect(DSN, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("Postgres not running (docker compose up -d postgres)")
    yield c
    c.close()
