"""Simulate the payment switch's monthly settlement file, with labelled defects (SIMULATED).

The switch only sees card withdrawals and interbank transfers. Its file is built from the real core
transactions, then defects are injected at fixed rates with a fixed seed. landing/switch/_labels.csv
is the answer key used by dq/evaluate.py; the pipeline never reads it.

Defects (one per row at most):
  reconciliation : missing_in_switch, missing_in_core, amount_mismatch, date_mismatch (>1 day), duplicate
  row validity   : null_account, negative_amount, bad_date_format, bad_currency
  negative control (NOT a defect): settlement_t1 = value date one day after posting, which is normal.
"""
import csv
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "landing" / "switch"
SWITCH_OPS = {"VYBER KARTOU": "CARD", "PREVOD NA UCET": "ACH", "PREVOD Z UCTU": "ACH"}
RATES = {"missing_in_switch": .003, "amount_mismatch": .002, "date_mismatch": .002, "duplicate": .002,
         "null_account": .001, "negative_amount": .001, "bad_date_format": .001, "bad_currency": .001,
         "settlement_t1": .02}
MISSING_IN_CORE_RATE = .001
COLS = ["switch_ref", "core_ref", "account_id", "value_date", "amount", "currency", "channel"]


def build(trans: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    t = trans[trans.operation.isin(SWITCH_OPS)].copy()
    t["date"] = pd.to_datetime("19" + t["date"], format="%Y%m%d")
    t = t.sort_values(["date", "trans_id"]).reset_index(drop=True)
    sw = pd.DataFrame({
        "switch_ref": [f"SW{i:08d}" for i in range(len(t))],
        "core_ref": t.trans_id, "account_id": t.account_id, "value_date": t.date,
        "amount": t.amount.astype(float), "currency": "CZK", "channel": t.operation.map(SWITCH_OPS),
        "_month": t.date.dt.strftime("%Y-%m")})  # one settlement file per core posting month

    kinds = list(RATES)
    p = np.array([RATES[k] for k in kinds])
    draw = rng.choice(len(kinds) + 1, size=len(sw), p=[*p, 1 - p.sum()])
    sw["issue"] = [kinds[d] if d < len(kinds) else None for d in draw]

    i = sw.issue
    sw.loc[i == "amount_mismatch", "amount"] += rng.choice([-1, 1], (i == "amount_mismatch").sum()) * \
        np.round(rng.uniform(1, 500, (i == "amount_mismatch").sum()), 2)
    sw.loc[i == "date_mismatch", "value_date"] += pd.to_timedelta(rng.integers(2, 6, (i == "date_mismatch").sum()), "D")
    sw.loc[i == "settlement_t1", "value_date"] += pd.Timedelta(days=1)
    sw.loc[i == "negative_amount", "amount"] *= -1

    sw["value_date"] = sw.value_date.dt.strftime("%Y-%m-%d")
    sw["amount"] = sw.amount.map(lambda x: f"{x:.2f}")
    sw.loc[i == "null_account", "account_id"] = ""
    sw.loc[i == "bad_date_format", "value_date"] = pd.to_datetime(sw.loc[i == "bad_date_format", "value_date"]).dt.strftime("%d/%m/%Y")
    sw.loc[i == "bad_currency", "currency"] = "EUR"

    dups = sw[i == "duplicate"].copy()          # retransmission: same switch_ref sent twice
    dups["issue"] = "duplicate_copy"
    n_extra = int(len(sw) * MISSING_IN_CORE_RATE)  # switch has it, core never posted it
    extra = sw[sw.issue.isna()].sample(n_extra, random_state=seed).copy()
    extra["switch_ref"] = [f"SX{k:08d}" for k in range(n_extra)]
    extra["core_ref"] = [str(900000000 + k) for k in range(n_extra)]
    extra["issue"] = "missing_in_core"

    labels = pd.concat([sw[sw.issue.notna()], extra])[["switch_ref", "core_ref", "issue"]]
    out = pd.concat([sw[i != "missing_in_switch"], dups, extra]).sort_values("switch_ref", kind="stable")
    return out, labels


def main() -> None:
    trans = pd.read_csv(ROOT / "data" / "raw" / "trans.asc", sep=";", dtype=str, keep_default_na=False)
    sw, labels = build(trans)
    OUT.mkdir(parents=True, exist_ok=True)
    for m, part in sw.groupby("_month"):
        part[COLS].to_csv(OUT / f"settlement_{m}.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    labels.to_csv(OUT / "_labels.csv", index=False)
    print(f"{sw['_month'].nunique()} files, {len(sw)} rows; injected:", labels.issue.value_counts().to_dict())


if __name__ == "__main__":
    main()
