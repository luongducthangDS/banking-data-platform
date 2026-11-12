# Progress

## Trạng thái (2026-11-12)
Cả 4 module chạy end to end. Chạy lại từ DB trống qua Airflow: 72/72 run thành công trong 44 phút. Git local, chưa có remote.

| Module | Kết quả đã đo |
|---|---|
| Pipeline | 1.066.765 dòng API giao, 10.445 bản giao trùng bị loại, 1.056.320 dòng raw = core, tổng tiền khớp; nạp lại 1 tháng chèn 0 dòng |
| Analytics | 5 mart, 6 insight sinh từ SQL (`reports/insights.md`), 11 file SQL phỏng vấn chạy qua test |
| DQ & recon | 3.979/3.979 lỗi cấy được phát hiện, precision 1,0; 0/5.573 ca T+1 hợp lệ bị báo nhầm (`reports/dq_eval.md`) |
| Assistant | 28/30 execution accuracy, 12/12 câu tấn công an toàn, p50 3,0 s (`reports/assistant_eval.md`) |

Test: `python -m pytest -q` → 39 passed.

## Hạn chế đã biết (ghi rõ khi phỏng vấn/CV)
- Recall 100 % của DQ chỉ chứng minh rule cài đúng, vì rule được viết khi đã biết loại lỗi cấy.
- Churn là proxy (Berka không có đóng tài khoản). mart_customer_360 dùng mốc cố định 1998, nên trong lúc backfill giữa chừng các cột "1998" chưa có nghĩa.
- Assistant: lỗi fan-out khi join mart tháng với `dim_date` (q05); câu "khách hàng theo vùng" mơ hồ (q20). 12 câu tấn công đều bị model từ chối nên lớp guard chỉ được kiểm bằng unit test (17 ca).
- Power BI `.pbix` chưa dựng (user tự làm theo `analytics/powerbi/README.md`).
- p95 latency 20,7 s là do chờ 429 của Gemini free tier.

## Bug tìm thấy khi đo
- GX chỉ trả 20 dòng lỗi/rule nếu không đặt `partial_unexpected_count` → bằng chứng thiếu (duplicate recall đo ra 80,8 %); đã sửa.
- mart_account_monthly tạo tháng tương lai khi backfill → NULL `end_balance`; test `not_null` chặn DAG; đã sửa.
- File switch lúc đầu gom theo ngày giá trị → ca T+1 cuối tháng rơi sang file tháng sau, sinh break giả; đổi sang gom theo tháng ghi sổ.

## Bước tiếp theo
Mục chưa tick trong `TASKS.md` (Power BI, tạo repo GitHub + CI).
