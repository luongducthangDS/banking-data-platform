# Tasks

## Module 1: Pipeline
- [ ] Docker Compose: Postgres + core-api; `sources/make_landing.py`
- [ ] `pipeline/`: load_files (full), load_transactions (incremental, retry, idempotent), meta tables
- [ ] dbt: staging + core + tests
- [ ] Airflow image + DAG `bank_pipeline`; backfill 72 tháng chạy hết
- [ ] Test idempotent + khớp tổng tiền với nguồn

## Module 2: Analytics
- [ ] dbt marts + test
- [ ] `docs/KPI_DEFINITIONS.md`, `analytics/insights.py` → `reports/insights.md`
- [ ] `analytics/powerbi/` spec + DAX
- [ ] `analytics/sql/` câu SQL phỏng vấn trên schema, có test chạy được

## Module 3: DQ & Reconciliation
- [ ] `dq/inject.py` tạo switch feed + nhãn
- [ ] GX checks + SQL rules → `dq.*`
- [ ] Đối soát → `recon.*`; eval precision/recall
- [ ] DAG `dq_recon`, `dq-api`

## Module 4: Assistant
- [ ] Role `analyst_ro`; text2sql + guard + retry
- [ ] FastAPI + Streamlit
- [ ] Bộ câu gold + tấn công; eval

## Chung
- [ ] README, PROGRESS, commit
