"""CLI used by Airflow tasks and for local runs.

  python -m pipeline.cli files
  python -m pipeline.cli transactions 1993-01-01 1993-02-01
  python -m pipeline.cli backfill 1993-01-01 1999-01-01      # month by month, no Airflow
"""
import logging
import sys
from datetime import date

from pipeline.extract_load import connect, load_files, load_transactions


def months(start: date, end: date):
    while start < end:
        nxt = date(start.year + start.month // 12, start.month % 12 + 1, 1)
        yield start, min(nxt, end)
        start = nxt


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cmd, *args = argv
    with connect() as conn:
        if cmd == "files":
            load_files(conn)
        elif cmd == "transactions":
            load_transactions(conn, date.fromisoformat(args[0]), date.fromisoformat(args[1]))
        elif cmd == "backfill":
            for s, e in months(date.fromisoformat(args[0]), date.fromisoformat(args[1])):
                load_transactions(conn, s, e)
        else:
            raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
