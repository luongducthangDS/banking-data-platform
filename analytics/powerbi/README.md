# Power BI dashboard: cách dựng

File `.pbix` dựng tay trong Power BI Desktop (không sinh được bằng code). Mọi logic nằm ở dbt; Power BI chỉ đọc mart và có vài measure DAX.

## 1. Kết nối
Get Data → PostgreSQL database → Server `localhost:5433`, Database `bank`, chế độ **Import**.
Đăng nhập: user `analyst_ro`, mật khẩu trong `.env` (chỉ đọc được `core` và `marts`).
Nếu Power BI báo thiếu driver: cài Npgsql theo hướng dẫn của Microsoft, hoặc dùng ODBC (psqlODBC).

Bảng cần load:
`marts.mart_monthly_kpi`, `marts.mart_customer_360`, `marts.mart_loan_performance`, `marts.mart_district_kpi`, `core.dim_date`, `dq.check_results`, `recon.daily_summary` (2 bảng cuối cho trang Chất lượng dữ liệu, có sau khi chạy module DQ).

## 2. Model
- `mart_monthly_kpi[month_start]` → `dim_date[date]` (nhiều-một). Đánh dấu `dim_date` là Date table.
- `mart_customer_360`, `mart_loan_performance`, `mart_district_kpi` dùng riêng, không cần quan hệ (đã denormalize trong dbt).
- Measure: copy từ `measures.dax`.

## 3. Trang và visual
Màu theo `docs/DESIGN.md`: chính `#1F4E79`, cảnh báo `#C55A11`, so sánh `#7F7F7F`.

**Trang 1: Tổng quan**
- 4 card: `Total Deposits (latest)`, `Open Accounts (latest)`, `Active Rate (latest)`, `Deposits YoY %`.
- Line chart: `month_start` × `total_deposits`; thêm line `credit_amount`.
- Clustered column: `year` × `new_accounts`, `new_loans`.
- Slicer: năm.

**Trang 2: Khách hàng**
- Bar chart: `rfm_segment` × số khách; tooltip: số dư bình quân, `Churn Risk Rate`.
- Matrix: `rfm_segment` (hàng) × `has_card` (cột), giá trị số khách.
- Card: `Churn Risk Customers`, `Churn Risk Deposits`.
- Table: top 20 khách churn risk theo `avg_end_balance_1998` (danh sách gọi điện giữ chân).
- Slicer: `region`, `age_band`, `gender`.

**Trang 3: Khoản vay & thẻ**
- Card: `Loan Default Rate`, `Defaulted Amount`.
- Column: `amount_band` × `Loan Default Rate`.
- Column: tín hiệu trước khi duyệt (`n_penalty_interest_before > 0`, `min_end_balance_6m < 5000`) × `Loan Default Rate`.
- Filled map hoặc bar: `region` × `Loan Default Rate` (từ `mart_district_kpi`).

**Trang 4: Chất lượng dữ liệu**
- Table: rule, dimension, `unexpected_count`, trạng thái pass/fail của lần chạy mới nhất (`dq.check_results`).
- Line: `recon.daily_summary` số break theo ngày.

## 4. Ảnh chụp
Sau khi dựng, lưu `banking_dashboard.pbix` và ảnh từng trang vào `analytics/powerbi/screenshots/` để README hiển thị.
