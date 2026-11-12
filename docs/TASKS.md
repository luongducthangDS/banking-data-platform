# Tasks

## Module 1: Pipeline
- [x] Docker Compose: Postgres + core-api; `sources/make_landing.py`
- [x] `pipeline/`: load_files (full), load_transactions (incremental, retry, idempotent), meta tables
- [x] dbt: staging + core + tests
- [x] Airflow image + DAG `bank_pipeline`; backfill 72 tháng chạy hết từ DB trống
- [x] Test idempotent + khớp tổng tiền với nguồn

## Module 2: Analytics
- [x] dbt marts + test
- [x] `docs/KPI_DEFINITIONS.md`, `analytics/insights.py` → `reports/insights.md`
- [x] `analytics/powerbi/` spec + DAX
- [ ] User dựng `.pbix` trong Power BI Desktop, lưu ảnh vào `analytics/powerbi/screenshots/`
- [x] `analytics/sql/` câu SQL phỏng vấn trên schema, có test chạy được

## Module 3: DQ & Reconciliation
- [x] `dq/inject.py` tạo switch feed + nhãn
- [x] GX checks + SQL rules → `dq.*`
- [x] Đối soát → `recon.*`; eval precision/recall
- [x] DAG có dq_checks + reconcile, `dq-api`

## Module 4: Assistant
- [x] Role `analyst_ro`; text2sql + guard + retry
- [x] FastAPI + Streamlit
- [x] Bộ câu gold + tấn công; eval

## Tiếp theo (tuỳ chọn)
- [ ] Assistant: thêm vào catalog cảnh báo "không join mart tháng với dim_date theo month_start" (lỗi q05), rồi đo lại
- [ ] Tạo repo GitHub public + CI (pytest offline: guard, inject, pipeline unit)
- [ ] DQ: nới dung sai CORE-CONS-02 lên 0,20 cho ngày có ≥ 2 bút toán ngân hàng tự sinh
