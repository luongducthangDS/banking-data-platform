import pytest

from assistant.guard import MAX_ROWS, Blocked, check

OK = [
    "select year_month, total_deposits from marts.mart_monthly_kpi order by month_start",
    "with x as (select region, count(*) n from marts.mart_customer_360 group by 1) select * from x",
    "select region from marts.mart_district_kpi union select region from core.dim_account",
]
ATTACKS = [
    "drop table core.fact_transactions",
    "delete from marts.mart_customer_360",
    "select 1; drop table core.dim_customer",
    "update core.fact_loans set status = 'A'",
    "select * from raw.transactions",
    "select * from meta.pipeline_runs",
    "select * from pg_catalog.pg_user",
    "select * from information_schema.tables",
    "select pg_sleep(60)",
    "select pg_read_file('/etc/passwd')",
    "select * from dim_customer",                      # unqualified = not allow-listed
    "copy core.dim_customer to '/tmp/x.csv'",
    "select * from core.dim_customer for update",
    "create table marts.x as select 1",
    "set statement_timeout = 0",
    "select set_config('statement_timeout', '0', false)",
    "grant select on core.dim_customer to public",
]


@pytest.mark.parametrize("sql", OK)
def test_allowed(sql):
    assert f"LIMIT {MAX_ROWS}" in check(sql)


@pytest.mark.parametrize("sql", ATTACKS)
def test_blocked(sql):
    with pytest.raises(Blocked):
        check(sql)


def test_existing_small_limit_kept_and_large_capped():
    assert "LIMIT 5" in check("select * from marts.mart_monthly_kpi limit 5")
    assert f"LIMIT {MAX_ROWS}" in check("select * from marts.mart_monthly_kpi limit 999999")
