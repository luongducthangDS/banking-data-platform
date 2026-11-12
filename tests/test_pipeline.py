from datetime import date

import pandas as pd
import pytest
import requests

from pipeline import extract_load as el
from pipeline.cli import months
from tests.conftest import ROOT


def test_months_split_cover_range_without_gaps():
    m = list(months(date(1993, 1, 1), date(1994, 1, 1)))
    assert len(m) == 12 and m[0] == (date(1993, 1, 1), date(1993, 2, 1)) and m[-1][1] == date(1994, 1, 1)


class FlakySession:
    """Fails with 503 `fails` times, then answers."""
    def __init__(self, fails, status=503):
        self.fails, self.status, self.calls = fails, status, 0

    def get(self, *a, **k):
        self.calls += 1
        r = requests.Response()
        if self.calls <= self.fails:
            r.status_code = self.status
            return r
        r.status_code, r._content = 200, b'{"data": [], "total_pages": 1}'
        return r


def test_fetch_retries_transient_errors(monkeypatch):
    monkeypatch.setattr(el.time, "sleep", lambda s: None)
    s = FlakySession(fails=3)
    assert el.fetch_page(date(1993, 1, 1), date(1993, 2, 1), 1, session=s)["total_pages"] == 1
    assert s.calls == 4


def test_fetch_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(el.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError):
        el.fetch_page(date(1993, 1, 1), date(1993, 2, 1), 1, retries=3, session=FlakySession(fails=10))


def test_fetch_does_not_retry_client_errors(monkeypatch):
    s = FlakySession(fails=10, status=422)
    with pytest.raises(requests.HTTPError):
        el.fetch_page(date(1993, 1, 1), date(1993, 2, 1), 1, session=s)
    assert s.calls == 1


def test_reload_is_idempotent_and_complete(conn):
    """Re-loading a month (API sends duplicates) adds 0 rows; raw holds exactly the source rows."""
    try:
        requests.get(f"{el.API}/health", timeout=3)
    except requests.ConnectionError:
        pytest.skip("core-api not running")
    start, end = date(1996, 3, 1), date(1996, 4, 1)
    el.load_transactions(conn, start, end)          # make sure the month is there
    again = el.load_transactions(conn, start, end)
    assert again["inserted"] == 0

    src = pd.read_csv(ROOT / "data" / "raw" / "trans.asc", sep=";", dtype=str, usecols=["trans_id", "date"])
    expected = set(src.loc[(src.date >= "960301") & (src.date < "960401"), "trans_id"])
    got = {r[0] for r in conn.execute(
        "select trans_id from raw.transactions where date >= '960301' and date < '960401'")}
    assert got == expected
