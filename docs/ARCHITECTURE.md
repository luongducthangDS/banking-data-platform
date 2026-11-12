# Architecture

## Luồng dữ liệu

```
 Nguồn (giả lập từ Berka)            Airflow DAG bank_pipeline (@monthly, 1993-01 → 1998-12, catchup)
 ─────────────────────────           ───────────────────────────────────────────────────────────────
 landing/crm/*.csv   (khách hàng,  ─┐
   tài khoản, quận, lệnh chuyển)    │  load_files      full load: TRUNCATE + COPY trong 1 transaction
 landing/lending/*.json (vay, thẻ) ─┤
 core-api  GET /transactions       ─┘  load_transactions incremental theo data interval,
   (FastAPI, phân trang, lỗi 503        retry + backoff, INSERT ... ON CONFLICT DO NOTHING,
    và giao trùng giả lập)               ghi meta.watermark + meta.pipeline_runs
                                          │
                                          ▼
 PostgreSQL `bank`:  raw ──dbt──▶ staging (view) ──▶ core (star schema) ──▶ marts
                                          │                                  │
                                 dbt build (test)                    Power BI / assistant
                                          │
            DAG dq_recon (sau pipeline): GX checks + đối soát core vs switch ──▶ dq.*, recon.*
                                          │
                                   dq-api (FastAPI)
```

## Schema trong Postgres `bank`
| Schema | Ai ghi | Nội dung |
|---|---|---|
| `raw` | pipeline/ | Bản sao nguồn, mọi cột là text, thêm `_batch_id`, `_loaded_at`, `_source` |
| `meta` | pipeline/ | `pipeline_runs` (log từng lần chạy), `watermark` |
| `staging` | dbt | View: ép kiểu, dịch mã tiếng Séc, chuẩn hoá rỗng → NULL |
| `core` | dbt | `dim_date`, `dim_district`, `dim_customer`, `dim_account`, `bridge_account_customer`, `fact_transactions` (incremental), `fact_loans`, `fact_cards`, `fact_orders` |
| `marts` | dbt | Bảng cho phân tích và Power BI |
| `dq`, `recon` | dq/ | Kết quả kiểm tra, dòng lỗi, đối soát |
| `switch` | dq/inject.py | Nguồn thứ hai (giả lập) để đối soát |

## Thư mục
```
sources/core_api/   FastAPI giả lập core banking (REST nguồn giao dịch)
sources/make_landing.py  tạo landing/ (CSV + JSON) từ data/raw/*.asc
pipeline/           extract + load (Python, psycopg), dùng bởi Airflow và CLI
warehouse/          dbt project (staging, core, marts, tests)
airflow/            Dockerfile + DAGs
dq/                 Great Expectations, đối soát, cấy lỗi, API
analytics/          insight, spec Power BI + DAX, SQL phỏng vấn
assistant/          Text-to-SQL (FastAPI + Streamlit), eval
tests/              pytest
```

## Stack
Python 3.11, PostgreSQL 16, dbt-postgres 1.9, Apache Airflow 2.10 (LocalExecutor), Great Expectations 1.x, FastAPI, Streamlit, sqlglot, Gemini (google-genai), Docker Compose.

Airflow chỉ điều phối: code nghiệp vụ, dbt và GX chạy trong venv `/opt/app` của image bằng `BashOperator`, để tránh xung đột thư viện với Airflow.
