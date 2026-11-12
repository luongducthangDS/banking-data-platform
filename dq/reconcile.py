"""Reconcile core banking against the payment switch settlement file for one month.

Match key: switch.core_ref = core.transaction_id, over the transactions the switch handles
(card withdrawals and interbank transfers). Value date may lag posting by 1 day (T+1 settlement).
Results: recon.breaks (one row per break), recon.daily_summary (totals per day for both sides),
and one row per break type in dq.check_results (dimension = reconciliation). Idempotent per interval.

  python -m dq.reconcile 1995-06-01 1995-07-01
"""
from __future__ import annotations

import logging
import sys
import uuid
from datetime import date

from pipeline.extract_load import connect

log = logging.getLogger("recon")
BREAK_TYPES = ["missing_in_switch", "missing_in_core", "amount_mismatch", "date_mismatch",
               "duplicate_in_switch", "invalid_switch_record"]
DATE_TOLERANCE_DAYS = 1

DDL = """
CREATE SCHEMA IF NOT EXISTS recon;
CREATE TABLE IF NOT EXISTS recon.breaks (
  run_id uuid NOT NULL, interval_start date NOT NULL, break_type text NOT NULL, switch_ref text,
  core_transaction_id bigint, account_id text, core_amount numeric(14,2), switch_amount text,
  core_date date, switch_value_date text);
CREATE INDEX IF NOT EXISTS breaks_interval ON recon.breaks (interval_start, break_type);
CREATE TABLE IF NOT EXISTS recon.daily_summary (
  interval_start date NOT NULL, day date NOT NULL, core_count int, core_amount numeric(16,2),
  switch_count int, switch_amount numeric(16,2), matched int, breaks int, PRIMARY KEY (day));
GRANT USAGE ON SCHEMA recon TO analyst_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA recon TO analyst_ro;
"""

CLASSIFY = f"""
create temp table recon_rows on commit drop as
with sw as (
    select switch_ref, core_ref, nullif(trim(account_id), '') as account_id, value_date as value_date_raw, amount as amount_raw,
           case when value_date ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$' then value_date::date end as value_date,
           case when amount ~ '^-?[0-9]+(\\.[0-9]+)?$' then amount::numeric end as amount,
           currency,
           row_number() over (partition by switch_ref order by ctid) as copy_no
    from raw.switch_settlements where _file = %(file)s
),
core as (
    select transaction_id, account_id, transaction_date, amount
    from core.fact_transactions
    where transaction_date >= %(start)s and transaction_date < %(end)s
      and operation in ('card_withdrawal', 'remittance_to_other_bank', 'collection_from_other_bank')
),
j as (
    select s.*, c.transaction_id, c.account_id as core_account_id, c.transaction_date, c.amount as core_amount
    from (select * from sw where copy_no = 1) s
    full outer join core c on c.transaction_id::text = s.core_ref
)
select case
         when transaction_id is null then 'missing_in_core'
         when switch_ref is null then 'missing_in_switch'
         when value_date is null or amount is null or currency <> 'CZK' or account_id is null
              then 'invalid_switch_record'
         when amount <> core_amount then 'amount_mismatch'
         when abs(value_date - transaction_date) > {DATE_TOLERANCE_DAYS} then 'date_mismatch'
         else 'matched'
       end as status, switch_ref, transaction_id, coalesce(account_id, core_account_id::text) as account_id,
       core_amount, amount_raw, transaction_date, value_date_raw, amount as switch_amount_num,
       coalesce(transaction_date, value_date) as day
from j
union all
select 'duplicate_in_switch', s.switch_ref, null, s.account_id, null, s.amount_raw, null, s.value_date_raw,
       s.amount, s.value_date
from sw s where copy_no > 1
"""


def run(start: date, end: date) -> dict[str, int]:
    run_id, file = uuid.uuid4(), f"settlement_{start:%Y-%m}.csv"
    with connect() as conn:
        conn.execute(DDL)
        with conn.transaction():
            conn.execute(CLASSIFY, {"file": file, "start": start, "end": end})
            counts = dict(conn.execute("select status, count(*) from recon_rows group by 1").fetchall())
            conn.execute("delete from recon.breaks where interval_start = %s", (start,))
            conn.execute("""insert into recon.breaks
                select %s, %s, status, switch_ref, transaction_id, account_id, core_amount, amount_raw,
                       transaction_date, value_date_raw
                from recon_rows where status <> 'matched'""", (run_id, start))
            conn.execute("delete from recon.daily_summary where interval_start = %s", (start,))
            conn.execute("""insert into recon.daily_summary
                select %s, day,
                       count(transaction_id), coalesce(sum(core_amount), 0),
                       count(switch_ref), coalesce(sum(switch_amount_num), 0),
                       count(*) filter (where status = 'matched'), count(*) filter (where status <> 'matched')
                from recon_rows where day >= %s and day < %s group by day""", (start, start, end))
            core_n = counts.get("matched", 0) + sum(counts.get(k, 0) for k in BREAK_TYPES if k not in ("missing_in_core", "duplicate_in_switch"))
            conn.execute("delete from dq.check_results where interval_start = %s and dimension = 'reconciliation'", (start,))
            for b in BREAK_TYPES:
                n = counts.get(b, 0)
                conn.execute("""insert into dq.check_results values (%s, now(), %s, %s, 'reconciliation', 'core vs switch',
                                %s, %s, %s, %s, 0, %s)""",
                             (run_id, start, f"RECON-{b}", f"reconciliation break: {b}", core_n, n,
                              round(100 * n / core_n, 4) if core_n else None, n == 0))
    log.info("recon %s: %s", start, counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2]))
