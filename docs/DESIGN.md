# Design (định dạng đầu ra)

## Bảng dữ liệu
- Tên cột `snake_case`, tiếng Anh. Mã tiếng Séc được dịch ở staging, giữ mã gốc ở cột `*_code`.
- Tiền tệ: CZK, `numeric(14,2)`. Ngày: `date`. Khoá ngày trong fact: `date_key int` dạng YYYYMMDD.
- Bảng `dq.*`/`recon.*` luôn có `run_id`, `checked_at`.

## Báo cáo (Markdown trong `reports/`)
- Mở đầu bằng 1 câu kết luận, sau đó là bảng số. Mọi số có nguồn (truy vấn hoặc file).
- Phần giả lập/lỗi cấy luôn được ghi rõ là giả lập.

## Power BI (`analytics/powerbi/`)
- 4 trang: Tổng quan, Khách hàng, Khoản vay & thẻ, Chất lượng dữ liệu.
- Màu: xanh đậm `#1F4E79` cho số chính, cam `#C55A11` cho cảnh báo/xấu, xám `#7F7F7F` cho so sánh. Font Segoe UI.
- KPI card trên cùng, xu hướng theo tháng ở giữa, bảng chi tiết dưới cùng.

## API
JSON, lỗi trả `{"detail": "..."}` với mã HTTP đúng nghĩa (400 SQL bị chặn, 503 nguồn lỗi).

## Assistant UI (Streamlit)
Ô hỏi, câu trả lời, SQL đã chạy (mở rộng được), bảng kết quả, biểu đồ khi kết quả có một cột thời gian/nhóm + một cột số.
