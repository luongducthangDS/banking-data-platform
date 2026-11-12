# Đánh giá Data Quality & Reconciliation

Lỗi trong file switch là **giả lập** (`dq/inject.py`, seed 42), có file đáp án. Dữ liệu core là Berka thật.
Chạy trên 72 tháng (`python -m dq.cli all 1993-01-01 1999-01-01`), rồi `python -m dq.evaluate`.

## Lỗi cấy: phát hiện được bao nhiêu

| injected          | detector          |   injected_rows |   detected |   recall |   flagged |   precision |
|:------------------|:------------------|----------------:|-----------:|---------:|----------:|------------:|
| null_account      | SW-COMP-01        |             261 |        261 |        1 |       261 |           1 |
| duplicate         | SW-UNIQ-01        |             573 |        573 |        1 |       573 |           1 |
| bad_date_format   | SW-VAL-01         |             279 |        279 |        1 |       279 |           1 |
| negative_amount   | SW-VAL-02         |             256 |        256 |        1 |       274 |           1 |
| bad_currency      | SW-VAL-03         |             267 |        267 |        1 |       267 |           1 |
| missing_in_switch | missing_in_switch |             871 |        871 |        1 |       871 |           1 |
| missing_in_core   | missing_in_core   |             281 |        281 |        1 |       281 |           1 |
| amount_mismatch   | amount_mismatch   |             604 |        604 |        1 |       860 |           1 |
| date_mismatch     | date_mismatch     |             587 |        587 |        1 |       587 |           1 |

Tổng: phát hiện 3979/3979 dòng lỗi cấy.

**Đối chứng âm:** 5573 giao dịch có ngày giá trị trễ 1 ngày (T+1, hợp lệ); bị báo nhầm là break: 0.

## Phát hiện trên dữ liệu thật (core, không có nhãn)

| rule         | description                                                               |   violations |   rows_checked |
|:-------------|:--------------------------------------------------------------------------|-------------:|---------------:|
| CORE-COMP-01 | interbank transfers name the partner bank                                 |            1 |  nan           |
| CORE-CONS-01 | transaction is not dated before the account was opened                    |            0 |  nan           |
| CORE-CONS-02 | day's closing balance = previous closing balance + day's net flow (±0.10) |            7 |  nan           |
| CORE-UNIQ-01 | transaction_id is unique                                                  |            0 |    1.05632e+06 |
| CORE-VAL-01  | transaction amount is greater than 0                                      |           14 |    1.05632e+06 |

- `CORE-VAL-01`: bút toán "lãi phạt" (`SANKC. UROK`) có số tiền 0,00 trong dữ liệu gốc. Nên loại ở staging hoặc hỏi lại hệ thống nguồn.
- `CORE-CONS-02`: đều là ngày cuối tháng có cả cộng lãi lẫn phí/lãi phạt; lệch khoảng 0,20 CZK = hai lần làm tròn 0,10.
  Không phải mất giao dịch. Nới dung sai lên 0,20 cho ngày có ≥ 2 bút toán ngân hàng tự sinh sẽ hết cảnh báo giả này.
- `CORE-COMP-01`: 1 giao dịch liên ngân hàng không ghi ngân hàng đối tác.

Mọi dòng vi phạm có trong `dq.error_records` và qua API `GET /dq/errors?rule_id=...`.
