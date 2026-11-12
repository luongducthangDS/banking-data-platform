# PRD: Banking Data Platform

## Vì sao có dự án này
Portfolio cho vị trí "AI Engineer – định hướng BA Data/DA/DE" trong mảng Banking (70 % Data, 30 % AI). Cần chứng minh SQL, ETL/ELT, data pipeline, data warehouse, data quality, và tích hợp AI vào bài toán dữ liệu cụ thể. Không phải dự án agentic.

## Người dùng (giả định)
- Data Engineer vận hành pipeline: cần biết pipeline chạy tới đâu, lỗi ở đâu, nạp lại có trùng không.
- Data Analyst / BA Data: cần mart sạch, KPI có định nghĩa rõ, dashboard Power BI.
- Bộ phận vận hành / đối soát: cần biết giao dịch nào lệch giữa hai hệ thống.
- Người dùng nghiệp vụ không biết SQL: hỏi bằng ngôn ngữ tự nhiên.

## Dữ liệu
PKDD'99 Financial (Berka), dữ liệu thật đã ẩn danh của một ngân hàng Séc 1993–1998: 4.500 tài khoản, 5.369 khách hàng, 1.056.320 giao dịch, 682 khoản vay, 892 thẻ, 6.471 lệnh chuyển tiền, 77 quận. Bản mirror: github.com/jlacko/berka-dataset.

Phần giả lập (phải nói rõ ở mọi nơi): việc tách thành 3 nguồn (file CSV, file JSON, REST API), lỗi mạng/giao trùng của API, và nguồn thứ hai để đối soát (switch feed) có lỗi cấy với nhãn đáp án.

## 4 module
1. **Pipeline (DE)**: extract từ CSV + JSON + REST API → raw → staging → core (star schema) bằng dbt; incremental theo tháng, idempotent, có watermark, retry, log; Airflow điều phối; chạy bằng Docker.
2. **Analytics & DWH (DA/BA)**: mart phân tích (KPI tháng, khách hàng hoạt động, phân khúc RFM, rời bỏ, hiệu quả khoản vay/thẻ, theo vùng); định nghĩa KPI; insight + khuyến nghị có số; spec + DAX cho Power BI; bộ câu SQL phỏng vấn trên schema này.
3. **Data Quality & Reconciliation**: quy tắc theo 6 chiều (completeness, uniqueness, validity, consistency, reconciliation, timeliness) bằng Great Expectations + SQL; đối soát core vs switch; bảng lỗi theo dòng; API FastAPI; đo tỷ lệ phát hiện so với nhãn cấy.
4. **AI Analytics Assistant**: hỏi tiếng Việt/Anh → SQL → kiểm tra sqlglot (chỉ SELECT, allowlist bảng, LIMIT) → user Postgres read-only + timeout → trả lời + biểu đồ; eval trên bộ câu có SQL đáp án (execution accuracy) và bộ câu tấn công.

## Mục tiêu đo được
- Pipeline chạy lại cùng một khoảng thời gian không làm tăng số dòng (idempotent); có test chứng minh.
- Toàn bộ 1.056.320 giao dịch vào `core.fact_transactions`, khớp tổng tiền với nguồn.
- DQ/recon: báo cáo precision/recall phát hiện lỗi cấy theo từng loại.
- Assistant: execution accuracy trên bộ câu gold; 100 % câu tấn công bị chặn.

## Non-goals
- Không streaming/CDC thật (chỉ mô phỏng incremental theo watermark).
- Không fine-tune LLM, không multi-agent, không LangGraph (một vòng sinh → kiểm → chạy → sửa là đủ).
- Không deploy cloud; chạy local bằng Docker Compose.
- File `.pbix` do user dựng trong Power BI Desktop (không tạo được bằng code).
