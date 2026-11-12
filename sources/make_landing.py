"""Simulate two file-based source systems from the Berka export.

- CRM drops semicolon CSV files (clients, accounts, dispositions, districts, standing orders) as-is.
- The lending system exports loans and cards as JSON arrays (values kept as the source strings).
Transactions are NOT here: they come from the core banking REST API (sources/core_api).
"""
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, LANDING = ROOT / "data" / "raw", ROOT / "landing"
CRM = {"client": "clients", "account": "accounts", "disp": "dispositions",
       "district": "districts", "order": "standing_orders"}
LENDING = {"loan": "loans", "card": "cards"}


def main() -> None:
    (LANDING / "crm").mkdir(parents=True, exist_ok=True)
    (LANDING / "lending").mkdir(parents=True, exist_ok=True)
    for src, name in CRM.items():
        shutil.copyfile(RAW / f"{src}.asc", LANDING / "crm" / f"{name}.csv")
    for src, name in LENDING.items():
        with open(RAW / f"{src}.asc", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        (LANDING / "lending" / f"{name}.json").write_text(json.dumps(rows), encoding="utf-8")
    print("landing ready:", sorted(p.name for p in LANDING.rglob("*.*")))


if __name__ == "__main__":
    main()
