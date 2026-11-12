"""Data quality checks for one monthly interval, run with Great Expectations; results go to dq.*.

Single-table rules use GX column expectations; cross-row/cross-table rules use GX
UnexpectedRowsExpectation with SQL. Timeliness is plain SQL on pipeline metadata.
Re-running an interval replaces that interval's results (idempotent).

  python -m dq.checks 1995-06-01 1995-07-01
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import date

import great_expectations as gx
from great_expectations.data_context.types.base import ProgressBarsConfig

from pipeline.extract_load import DSN, connect

log = logging.getLogger("dq")
MAX_ERROR_ROWS = 1000  # per rule and interval; the count is always exact

ASSETS = {
    "switch": """select switch_ref, core_ref, nullif(trim(account_id), '') as account_id, value_date, amount,
                        currency, channel
                 from raw.switch_settlements where _file = 'settlement_{month}.csv'""",
    "core_tx": """select * from core.fact_transactions
                  where transaction_date >= '{start}' and transaction_date < '{end}'""",
}

DDL = """
CREATE SCHEMA IF NOT EXISTS dq;
CREATE TABLE IF NOT EXISTS dq.check_results (
  run_id uuid NOT NULL, checked_at timestamptz NOT NULL, interval_start date NOT NULL, rule_id text NOT NULL,
  dimension text NOT NULL, target text NOT NULL, description text NOT NULL, element_count int,
  unexpected_count int NOT NULL, unexpected_pct numeric(7,4), threshold_pct numeric(7,4) NOT NULL,
  success boolean NOT NULL, PRIMARY KEY (interval_start, rule_id));
CREATE TABLE IF NOT EXISTS dq.error_records (
  run_id uuid NOT NULL, interval_start date NOT NULL, rule_id text NOT NULL, record_key text, record jsonb);
CREATE INDEX IF NOT EXISTS error_records_rule ON dq.error_records (interval_start, rule_id);
GRANT USAGE ON SCHEMA dq TO analyst_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA dq TO analyst_ro;
"""


@dataclass
class Rule:
    rule_id: str
    dimension: str
    asset: str
    description: str
    expectation: object
    key: str
    threshold_pct: float = 0.0


def rules() -> list[Rule]:
    E = gx.expectations
    return [
        Rule("SW-COMP-01", "completeness", "switch", "switch row has an account_id",
             E.ExpectColumnValuesToNotBeNull(column="account_id"), "switch_ref"),
        Rule("SW-UNIQ-01", "uniqueness", "switch", "switch_ref is unique within the settlement file",
             E.ExpectColumnValuesToBeUnique(column="switch_ref"), "switch_ref"),
        Rule("SW-VAL-01", "validity", "switch", "value_date is ISO YYYY-MM-DD",
             E.ExpectColumnValuesToMatchRegex(column="value_date", regex=r"^\d{4}-\d{2}-\d{2}$"), "switch_ref"),
        Rule("SW-VAL-02", "validity", "switch", "amount is a positive number with 2 decimals",
             E.ExpectColumnValuesToMatchRegex(column="amount", regex=r"^[0-9]+\.[0-9]{2}$"), "switch_ref"),
        Rule("SW-VAL-03", "validity", "switch", "currency is CZK",
             E.ExpectColumnValuesToBeInSet(column="currency", value_set=["CZK"]), "switch_ref"),
        Rule("SW-CONS-01", "consistency", "switch", "switch account_id equals the core account for the same transaction",
             E.UnexpectedRowsExpectation(description="account mismatch", unexpected_rows_query="""
                 select s.switch_ref, s.account_id, t.account_id as core_account_id
                 from {batch} s join core.fact_transactions t on t.transaction_id::text = s.core_ref
                 where s.account_id is not null and s.account_id <> t.account_id::text"""), "switch_ref"),
        Rule("CORE-UNIQ-01", "uniqueness", "core_tx", "transaction_id is unique",
             E.ExpectColumnValuesToBeUnique(column="transaction_id"), "transaction_id"),
        Rule("CORE-VAL-01", "validity", "core_tx", "transaction amount is greater than 0",
             E.ExpectColumnValuesToBeBetween(column="amount", min_value=0, strict_min=True), "transaction_id"),
        Rule("CORE-COMP-01", "completeness", "core_tx", "interbank transfers name the partner bank",
             E.UnexpectedRowsExpectation(description="partner bank missing", unexpected_rows_query="""
                 select transaction_id, account_id, operation from {batch}
                 where operation in ('remittance_to_other_bank', 'collection_from_other_bank')
                   and partner_bank is null"""), "transaction_id"),
        Rule("CORE-CONS-01", "consistency", "core_tx", "transaction is not dated before the account was opened",
             E.UnexpectedRowsExpectation(description="before opening", unexpected_rows_query="""
                 select t.transaction_id, t.transaction_date, a.opened_date
                 from {batch} t join core.dim_account a using (account_id)
                 where t.transaction_date < a.opened_date"""), "transaction_id"),
        # Anchored on the previous active day with exactly one transaction (its closing balance is known);
        # 0.10 CZK tolerance = rounding the source has on interest postings (analytics/sql/11_balance_consistency.sql).
        Rule("CORE-CONS-02", "consistency", "core_tx", "day's closing balance = previous closing balance + day's net flow (±0.10)",
             E.UnexpectedRowsExpectation(description="balance continuity", unexpected_rows_query="""
                 with days as (
                     select account_id, transaction_date, sum(signed_amount) as day_net, count(*) as n,
                            array_agg(balance_after) as balances
                     from core.fact_transactions group by 1, 2),
                 l as (select *, lag(balances[1]) over w as prev_eod, lag(n) over w as prev_n
                       from days window w as (partition by account_id order by transaction_date))
                 select l.account_id || ':' || l.transaction_date as day_key, l.prev_eod, l.day_net, l.balances
                 from l
                 where l.transaction_date in (select distinct transaction_date from {batch})
                   and l.prev_n = 1
                   and not exists (select 1 from unnest(l.balances) b where abs(l.prev_eod + l.day_net - b) <= 0.10)"""),
             "day_key"),
    ]


def _run_gx(rule: Rule, batch) -> tuple[int | None, int, list[dict]]:
    if isinstance(rule.expectation, gx.expectations.UnexpectedRowsExpectation):
        r = batch.validate(rule.expectation, result_format="COMPLETE")
        rows = r.result["details"]["unexpected_rows"]
        return None, int(r.result["observed_value"]), rows
    r = batch.validate(rule.expectation, result_format={
        "result_format": "COMPLETE", "unexpected_index_column_names": [rule.key],
        "partial_unexpected_count": MAX_ERROR_ROWS})  # GX caps the index list at 20 rows otherwise
    rows = r.result.get("unexpected_index_list") or []
    return r.result["element_count"], int(r.result["unexpected_count"]), rows


def _timeliness(conn, start: date, end: date) -> list[tuple]:
    """(rule_id, description, unexpected_count, element_count) for freshness of each source."""
    wm = conn.execute("select high_watermark from meta.watermark where source = 'core-api.transactions'").fetchone()
    stale = int(wm is None or wm[0] < end)
    sw = conn.execute("select count(*) from raw.switch_settlements where _file = %s",
                      (f"settlement_{start:%Y-%m}.csv",)).fetchone()[0]
    return [("TIME-01", "core transactions loaded through the end of the interval (watermark)", stale, 1),
            ("TIME-02", "switch settlement file for the interval has arrived", int(sw == 0), 1)]


def run(start: date, end: date) -> list[dict]:
    run_id = uuid.uuid4()
    ctx = gx.get_context(mode="ephemeral")
    ctx.variables.progress_bars = ProgressBarsConfig(globally=False)
    ds = ctx.data_sources.add_postgres("pg", connection_string=DSN.replace("postgresql://", "postgresql+psycopg://"))
    fmt = {"start": start, "end": end, "month": f"{start:%Y-%m}"}
    batches = {name: ds.add_query_asset(name, query=q.format(**fmt)).add_batch_definition_whole_table("all").get_batch()
               for name, q in ASSETS.items()}

    results, errors = [], []
    for rule in rules():
        n, bad, rows = _run_gx(rule, batches[rule.asset])
        pct = None if not n else round(100 * bad / n, 4)
        results.append(dict(rule_id=rule.rule_id, dimension=rule.dimension, target=rule.asset,
                            description=rule.description, element_count=n, unexpected_count=bad,
                            unexpected_pct=pct, threshold_pct=rule.threshold_pct,
                            success=(pct or 0) <= rule.threshold_pct if n else bad == 0))
        errors += [(rule.rule_id, str(r.get(rule.key)), json.dumps(r, default=str)) for r in rows[:MAX_ERROR_ROWS]]

    with connect() as conn:
        for rid, desc, bad, n in _timeliness(conn, start, end):
            results.append(dict(rule_id=rid, dimension="timeliness", target="meta", description=desc,
                                element_count=n, unexpected_count=bad, unexpected_pct=100.0 * bad / n,
                                threshold_pct=0.0, success=bad == 0))
        conn.execute(DDL)
        with conn.transaction():
            conn.execute("delete from dq.check_results where interval_start = %s and dimension <> 'reconciliation'", (start,))
            conn.execute("delete from dq.error_records where interval_start = %s and rule_id not like 'RECON-%%'", (start,))
            for r in results:
                conn.execute("""insert into dq.check_results values (%(run_id)s, now(), %(start)s, %(rule_id)s,
                    %(dimension)s, %(target)s, %(description)s, %(element_count)s, %(unexpected_count)s,
                    %(unexpected_pct)s, %(threshold_pct)s, %(success)s)""", {**r, "run_id": run_id, "start": start})
            with conn.cursor().copy("copy dq.error_records from stdin") as cp:
                for rid, key, rec in errors:
                    cp.write_row([run_id, start, rid, key, rec])
    failed = [r["rule_id"] for r in results if not r["success"]]
    log.info("dq %s: %s rules, failed=%s", start, len(results), failed)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("great_expectations").setLevel(logging.WARNING)
    run(date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2]))
