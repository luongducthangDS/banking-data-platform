-- Q: Xử lý duplicate trong bảng giao dịch thế nào?
-- 1) Định nghĩa "trùng": cùng khoá nghiệp vụ (transaction_id), hoặc cùng (account, ngày, số tiền, loại) nếu nguồn không có id.
-- 2) Giữ 1 bản bằng ROW_NUMBER() theo khoá, ưu tiên bản nạp sớm nhất; bỏ phần còn lại.
-- 3) Chặn từ gốc: PRIMARY KEY / UNIQUE + INSERT ... ON CONFLICT DO NOTHING (pipeline/extract_load.py làm vậy).
-- Bài: giả lập API giao lặp 2 lần cho 1 ngày, rồi khử trùng.
with delivered as (
    select transaction_id, account_id, amount, loaded_at from core.fact_transactions where date_key = 19980105
    union all
    select transaction_id, account_id, amount, loaded_at + interval '1 minute'
    from core.fact_transactions where date_key = 19980105 and transaction_id % 3 = 0
),
ranked as (
    select *, row_number() over (partition by transaction_id order by loaded_at) as rn from delivered
)
select (select count(*) from delivered)                 as delivered_rows,
       (select count(*) from ranked where rn > 1)       as duplicate_rows,
       (select count(*) from ranked where rn = 1)       as rows_after_dedupe;
