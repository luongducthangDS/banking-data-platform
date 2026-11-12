# KPI definitions

Một định nghĩa duy nhất cho mỗi KPI; SQL nằm ở model dbt ghi trong cột "Nguồn". Kỳ quan sát: 1993-01-01 → 1998-12-31; "ngày tham chiếu" = 1999-01-01 (`var as_of_date`).

## Yêu cầu nghiệp vụ (giả định cho bài toán)
1. Ban điều hành: tiền gửi và hoạt động tăng hay giảm theo tháng/năm, vùng nào đóng góp nhiều nhất.
2. Khối bán lẻ: khách nào giá trị cao, khách nào có nguy cơ rời bỏ, bán chéo thẻ cho ai.
3. Khối tín dụng: dấu hiệu nào có sẵn lúc duyệt vay báo trước vỡ nợ.

## KPI
| KPI | Định nghĩa | Nguồn |
|---|---|---|
| Open accounts | Số tài khoản đã mở tính đến tháng đó (Berka không có đóng tài khoản) | `mart_monthly_kpi.open_accounts` |
| Active account (tháng) | Có ≥ 1 giao dịch **do khách thực hiện** trong tháng. Loại giao dịch ngân hàng tự sinh: lãi (`UROK`), phí sao kê (`SLUZBY`), lãi phạt (`SANKC. UROK`) | `mart_account_monthly.is_active` |
| Active rate | Active accounts / open accounts | `mart_monthly_kpi.active_rate` |
| Credit / debit volume | Tổng `amount` theo chiều tiền vào / ra trong tháng | `mart_monthly_kpi` |
| Net flow | Credit − debit | `mart_monthly_kpi.net_flow` |
| Month-end balance | Số dư sau giao dịch cuối cùng của tháng; tháng không giao dịch lấy số dư tháng trước (carry forward). Cùng ngày thì giao dịch có `transaction_id` lớn hơn được coi là sau | `mart_account_monthly.end_balance` |
| Total deposits | Tổng month-end balance mọi tài khoản (gồm cả số dư âm) | `mart_monthly_kpi.total_deposits` |
| Default (vỡ nợ) | Khoản vay trạng thái B (kết thúc, chưa trả hết) hoặc D (đang chạy, có nợ) | `fact_loans.is_default` |
| Default rate | Số khoản default / số khoản vay | `mart_loan_performance`, `mart_district_kpi` |
| Payment-to-income | Khoản trả hằng tháng / tiền vào bình quân tháng trong 6 tháng trước ngày duyệt | `mart_loan_performance.payment_to_income` |
| Dormant | Không có giao dịch do khách thực hiện từ 1998-07-01 | `mart_customer_360.is_dormant` |
| Churn risk (proxy) | Tài khoản mở trước 1997-07-01, tiền vào 07–12/1998 < 50 % của 07–12/1997. So cùng kỳ để loại mùa vụ | `mart_customer_360.is_churn_risk` |
| RFM | R = số ngày từ giao dịch do khách thực hiện gần nhất; F = số giao dịch do khách thực hiện năm 1998; M = month-end balance bình quân 1998. Mỗi chiều chia 5 nhóm bằng `ntile` | `mart_customer_360` |

## Vì sao churn là proxy
Berka không có ngày đóng tài khoản. Chỉ 16/4.500 tài khoản không có giao dịch do khách thực hiện trong 6 tháng cuối (lệnh chuyển tiền định kỳ vẫn chạy), nên "ngừng giao dịch" không phân biệt được ai sắp đi. Dòng tiền vào giảm mạnh so với cùng kỳ (lương/thu nhập chuyển sang ngân hàng khác) là tín hiệu thực tế hơn; cần được kiểm chứng khi có dữ liệu đóng tài khoản thật.

## Phân khúc RFM (thứ tự xét từ trên xuống)
| Segment | Điều kiện |
|---|---|
| Champions | R ≥ 4, F ≥ 4, M ≥ 4 |
| Loyal | F ≥ 4, M ≥ 3 |
| At risk | R ≤ 2, F ≥ 3 |
| Hibernating | R ≤ 2, F ≤ 2 |
| Potential | R ≥ 3, F ≤ 3 |
| Needs attention | còn lại |
