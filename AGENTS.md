# banking-data-platform: agent notes

Đọc trước khi làm: [docs/RULES.md](docs/RULES.md) (bất biến) > [docs/PRD.md](docs/PRD.md) > [ARCHITECTURE](docs/ARCHITECTURE.md), [DESIGN](docs/DESIGN.md), [KPI_DEFINITIONS](docs/KPI_DEFINITIONS.md), [TASKS](docs/TASKS.md), [PROGRESS](docs/PROGRESS.md).

## Trạng thái (2026-11-12)
- Portfolio cho JD "AI Engineer – định hướng BA Data/DA/DE" (Banking, 70 % Data / 30 % AI). Một repo, 4 module: pipeline (Airflow + dbt + Postgres), analytics/DWH (mart, KPI, Power BI spec, SQL phỏng vấn), DQ & reconciliation (GX + SQL), AI assistant (Text-to-SQL có guard).
- Dữ liệu Berka thật (gitignored, `scripts/download_data.py`). Phần giả lập: tách 3 nguồn, lỗi API, file switch có lỗi cấy (`dq/inject.py`, nhãn ở `landing/switch/_labels.csv`).
- Git local, **chưa có remote**; user tự tạo repo GitHub public.
- Số liệu và việc còn lại: `docs/PROGRESS.md`.

## Gotchas
- Postgres ở cổng **5433** (máy có Supabase local ở 54322). User ghi `bank`/`bank`; assistant và dq-api dùng `analyst_ro` (chỉ đọc core, marts, dq, recon).
- dbt-core 1.12: test generic phải viết dạng `{accepted_values: {arguments: {values: [...]}}}`.
- Chạy dbt local: `cd warehouse && ../.venv/Scripts/dbt build --profiles-dir .`.
- Thứ tự giao dịch trong cùng ngày không suy ra được từ `trans_id`; số dư lệch ±0,10 CZK ở giao dịch cộng lãi. Mọi kiểm tra số dư phải theo ngày, có dung sai.
- Berka không có đóng tài khoản: churn chỉ là proxy (xem KPI_DEFINITIONS).
- `.env` có `GOOGLE_API_KEY`, `_2`, `_3` copy từ neuro-symbolic-agent; `gemini-3.5-flash` free tier chỉ ~20 request/ngày, model chính là flash-lite.
- Console Windows: chạy script in tiếng Việt với `PYTHONUTF8=1`.
- `.gitattributes` ép LF: `docker/postgres-init.sh` có CRLF sẽ làm container Postgres lỗi khi init.
