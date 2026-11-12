# Banking Data Platform

End-to-end data platform for a retail bank, built on real anonymised banking data (PKDD'99 "Berka": a Czech bank, 1993–1998, 1,056,320 transactions, 4,500 accounts, 682 loans, 892 cards).

Four modules, one `docker compose up`:

| # | Module | What it shows | Stack |
|---|---|---|---|
| 1 | [Pipeline](#1-pipeline-elt) | Multi-source extract, raw → staging → star schema, incremental + idempotent loads, orchestration | Python, PostgreSQL, dbt, Airflow, Docker |
| 2 | [Analytics & DWH](#2-analytics--data-warehouse) | Marts, KPI definitions, business insights, Power BI, SQL | dbt, SQL, Power BI |
| 3 | [Data Quality & Reconciliation](#3-data-quality--reconciliation) | 6 DQ dimensions, core-vs-switch reconciliation, measured detection rate | Great Expectations, SQL, FastAPI |
| 4 | [AI Analytics Assistant](#4-ai-analytics-assistant) | Natural-language questions → guarded, read-only SQL, evaluated on a gold set | Gemini, sqlglot, FastAPI, Streamlit |

**What is real and what is simulated.** The bank data is real (anonymised). Simulated: splitting it into three source systems (CSV, JSON, REST API), the API's transient failures and duplicate deliveries, and the payment switch file used for reconciliation, whose defects are injected with a fixed seed and an answer key.

```
 landing/crm/*.csv ─┐                    Airflow DAG bank_pipeline (@monthly, 72 runs 1993-01 → 1998-12)
 landing/lending/*.json ─┼─ load_files ───────┐
 core-api (REST) ───┼─ load_transactions ─┼─> dbt build ─> dq_checks (GX) ─> reconcile
 landing/switch/*.csv ─┘─ load_switch ───────┘   raw → staging → core → marts      dq.*, recon.*
                                                                │
                                         Power BI · assistant (analyst_ro, read-only) · dq-api
```

## Quick start

```bash
cp .env.example .env                    # add GOOGLE_API_KEY for the assistant
python scripts/download_data.py         # Berka files -> data/raw/
python sources/make_landing.py          # CRM CSV + lending JSON -> landing/
python -m dq.inject                     # simulated switch settlement files -> landing/switch/
docker compose up -d --build
```

Airflow at http://localhost:8080 (admin / `AIRFLOW_ADMIN_PASSWORD`): unpause `bank_pipeline`; it backfills 72 months.
Without Airflow: `python -m pipeline.cli files && python -m pipeline.cli backfill 1993-01-01 1999-01-01`, then `dbt build` in `warehouse/` and `python -m dq.cli all 1993-01-01 1999-01-01`.

| Service | URL |
|---|---|
| Airflow | http://localhost:8080 |
| Core banking API (simulated source) | http://localhost:8001/docs |
| DQ & reconciliation API | http://localhost:8002/docs |
| Assistant API | http://localhost:8003/docs |
| Assistant UI | http://localhost:8501 |
| PostgreSQL | localhost:5433, db `bank` |

Tests: `python -m pytest -q` (tests needing Postgres skip when it is down).

---

## 1. Pipeline (ELT)

- **Sources.** CRM drops semicolon CSV (clients, accounts, dispositions, districts, standing orders); the lending system exports JSON (loans, cards); transactions come from a paginated REST API that fails with 503 on 5 % of requests and re-sends 1 % of rows (at-least-once delivery).
- **Raw layer** keeps source strings plus `_batch_id`, `_loaded_at`, `_source`. Reference data: full load (TRUNCATE + COPY in one transaction, so a failure never leaves a half-loaded snapshot). Transactions: incremental per data interval, retries with exponential backoff (4xx fail fast), `DISTINCT ON` + `INSERT … ON CONFLICT DO NOTHING`, watermark in `meta.watermark`, every run (including failures) in `meta.pipeline_runs`.
- **dbt.** `staging` views type and translate the Czech source (YYMMDD dates, `birth_number` with +50 on the month for women, `''` and `' '` both meaning missing, `?` in district stats, codes like `PRIJEM`/`VYDAJ`/`SIPO`). `core` is a star schema: `fact_transactions` (incremental merge on `loaded_at`), `fact_loans`, `fact_cards`, `fact_standing_orders`, `dim_customer`, `dim_account`, `dim_district`, `dim_date`, `bridge_account_customer`. Tests: keys, relationships, accepted values, and a singular test that core reconciles with raw on row count and total amount.
- **Airflow** only orchestrates; business code, dbt and GX run in their own venv in the image (`BashOperator`), so their dependencies never fight Airflow's.

Measured:
- Re-running a loaded month inserts 0 rows; the API's duplicate deliveries are dropped (e.g. 577 delivered → 572 inserted for 1993-01..02). `tests/test_pipeline.py` checks raw equals the source file for a month after a reload.
- From an empty database, Airflow backfilled **72/72 monthly runs** (load → `dbt build` with 72 tests → DQ → reconciliation) in 44 min: 1,066,765 rows delivered by the API, **10,445 duplicate deliveries dropped**, 1,056,320 in raw and in `core.fact_transactions`, total amount equal to the source.
- That fresh run caught a real bug: `mart_account_monthly` built months up to 1998-12 while only the first month was loaded, so `end_balance` was NULL for future months; the `not_null` test failed the DAG. Fixed by limiting the grid to loaded months.

## 2. Analytics & Data Warehouse

Marts (`warehouse/models/marts`): `mart_account_monthly` (account × month grid with carried-forward month-end balance), `mart_monthly_kpi`, `mart_customer_360` (RFM, churn proxies, products), `mart_loan_performance` (borrower behaviour in the 6 months before the grant), `mart_district_kpi`.

- KPI definitions and business requirements: [docs/KPI_DEFINITIONS.md](docs/KPI_DEFINITIONS.md).
- Insights with recommendations, every number generated by `analytics/insights.py`: [reports/insights.md](reports/insights.md).
- Power BI: connection, model, 4 pages, DAX measures in [analytics/powerbi/](analytics/powerbi/) (the `.pbix` is built by hand in Power BI Desktop).
- SQL interview set on this schema (WHERE vs HAVING, joins/anti-join, ROW_NUMBER/RANK/DENSE_RANK, dedupe, EXPLAIN + index, OLTP design, LAG growth, cohorts, gaps-and-islands, balance consistency): [analytics/sql/](analytics/sql/), each file executed by `tests/test_sql_examples.py`.

Findings (from `reports/insights.md`):
- Deposits grew 37.1 → 197.1 M CZK (×5.3) from Dec 1993 to Dec 1998; monthly active rate stays ~99 %, so "stopped transacting" cannot identify churn here (only 16 of 4,500 accounts were dormant for 6 months). Churn is therefore a proxy: credit inflow in H2-1998 below 50 % of H2-1997 (240 customers, 5.9 %).
- Loans whose borrower had penalty interest (overdraft) before the grant date defaulted 89.7 % (26/29) vs 5.2 % with no warning signal; both signals are known at decision time.
- Default rate rises with size: 4.0 % under 50k CZK vs 20.7 % above 300k.
- An index on `(account_id, transaction_date)` turns an account-statement query from a ~50 ms parallel seq scan into a ~0.1 ms index scan ([06_slow_query_explain.sql](analytics/sql/06_slow_query_explain.sql)).
- The source balance column has a ±0.10 CZK rounding drift on interest postings, and same-day transaction order cannot be recovered from `trans_id` (ordering by it breaks 50 % of balance chains), so balance consistency is checked per day with a 0.10 tolerance.

## 3. Data Quality & Reconciliation

Each monthly run checks the new data, writes results to `dq.check_results` (one row per rule and month), offending rows to `dq.error_records`, and reconciliation breaks to `recon.breaks` / `recon.daily_summary`. `dq-api` exposes them read-only (`/dq/summary`, `/dq/results`, `/dq/errors`, `/recon/summary`, `/recon/breaks`); Power BI page 4 reads the same tables.

| Dimension | Rules |
|---|---|
| Completeness | switch row has an account; interbank transfers name the partner bank |
| Uniqueness | `switch_ref` unique in the file; `transaction_id` unique |
| Validity | ISO value date, positive 2-decimal amount, currency = CZK; core amount > 0 |
| Consistency | switch account = core account; no transaction before account opening; day-level balance continuity (±0.10) |
| Reconciliation | core vs switch on `core_ref`: missing either side, amount, value date beyond T+1, duplicate, invalid record |
| Timeliness | watermark covers the interval; switch file arrived (a missing file fails `load_switch` and Airflow retries) |

Single-table rules are Great Expectations column expectations; cross-table rules are GX `UnexpectedRowsExpectation` SQL; reconciliation is one `FULL OUTER JOIN` classification query.

Measured on 72 months ([reports/dq_eval.md](reports/dq_eval.md)), against the injected answer key:
- **3,979 / 3,979 injected defects detected**, precision 1.0 for every detector (a negative amount also counts as an amount break, which is correct).
- **0 / 5,573** legitimate T+1 settlements flagged (negative control).
- Caveat: the rules were written knowing the injected defect types, so this proves the checks are implemented correctly, not that they catch unknown defects.
- On the real core data: 14 penalty-interest postings of 0.00 CZK, 1 interbank transfer without partner bank, and 7 month-end days off by ~0.20 CZK (two stacked 0.10 roundings, not lost transactions).
- Bug found while measuring: GX returns only 20 offending rows per check unless `partial_unexpected_count` is raised; counts were right but stored evidence was incomplete (first run showed 80.8 % for duplicates).

## 4. AI Analytics Assistant

```
question ─> LLM writes one SELECT (or declines) ─> sqlglot guard ─> EXPLAIN cost limit ─> run as analyst_ro
        <─ LLM answers from the returned rows only <─ rows + chart spec <──────── (read-only tx, 10 s timeout)
             failed SQL + error goes back to the LLM, at most 3 attempts
```

Safety in three layers: (1) `assistant/guard.py` parses with sqlglot and allows exactly one SELECT/UNION over `core.*`/`marts.*`, rejects write/DDL nodes, `FOR UPDATE`, `pg_*`/`dblink`/`set_config` functions, and caps `LIMIT` at 1000; (2) the database role `analyst_ro` has SELECT on `core`, `marts`, `dq`, `recon` only, read-only transactions by default and a 10 s statement timeout; (3) queries with an EXPLAIN cost above 2M are refused. The catalog given to the model ([assistant/catalog.md](assistant/catalog.md)) defines "now" as the end of the data (1998-12).

Measured with `gemini-3.5-flash-lite`, temperature 0 ([reports/assistant_eval.md](reports/assistant_eval.md)):

| Metric | Result |
|---|---|
| Execution accuracy on 30 gold questions (VN + EN) | **28/30** |
| SQL executed successfully (≤ 3 attempts) / first attempt | 30/30 / 29/30 |
| Attack prompts ending safely (DROP, UPDATE, raw/meta/pg_catalog, pg_sleep, prompt leak, SQL injection in text, off-topic) | **12/12** |
| Latency p50 / p95 (two LLM calls) | 3.0 s / 20.7 s (p95 is free-tier 429 back-off) |

The two misses: q05 joined the monthly mart to the daily `dim_date` on `month_start`, multiplying every month ~30× (join fan-out, a real error); q20 counted 4,500 account owners by account region while the reference counts 5,369 clients (owners + disponents) by home region (ambiguous question). All 12 attacks were refused by the model itself, so the guard was not exercised by this run; it is tested directly by 17 attack cases in `tests/test_guard.py`.

## Repository

```
sources/      simulated source systems (core banking API, landing files)
pipeline/     extract + load (raw, meta), CLI used by Airflow
warehouse/    dbt project: staging, core (star schema), marts, tests
airflow/      image + DAG
dq/           GX checks, reconciliation, defect injection, evaluation, API
analytics/    insights, Power BI spec + DAX, SQL interview set
assistant/    text-to-SQL guard + execution, API, UI, eval sets
docs/         PRD, architecture, design, rules, tasks, progress, KPI definitions
reports/      generated reports (insights, DQ evaluation, assistant evaluation)
```

Data: PKDD'99 Discovery Challenge financial dataset (Petr Berka), mirror at github.com/jlacko/berka-dataset.
