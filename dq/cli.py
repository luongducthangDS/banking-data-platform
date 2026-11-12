"""python -m dq.cli month 1995-06-01 1995-07-01   # checks + reconciliation for one interval
   python -m dq.cli all 1993-01-01 1999-01-01      # every month (no Airflow)"""
import logging
import sys
from datetime import date

from dq import checks, reconcile
from pipeline.cli import months


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    cmd, start, end = argv[0], date.fromisoformat(argv[1]), date.fromisoformat(argv[2])
    spans = [(start, end)] if cmd == "month" else list(months(start, end))
    for s, e in spans:
        checks.run(s, e)
        reconcile.run(s, e)


if __name__ == "__main__":
    main(sys.argv[1:])
