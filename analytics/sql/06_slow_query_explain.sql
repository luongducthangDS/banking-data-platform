-- Q: Query chạy chậm thì xử lý thế nào?
-- 1) EXPLAIN (ANALYZE, BUFFERS) xem plan: Seq Scan trên bảng lớn? ước lượng rows lệch xa thực tế (cần ANALYZE)?
-- 2) Thêm index đúng cột lọc/join theo thứ tự (cột so sánh bằng trước, cột khoảng sau).
-- 3) Chỉ lấy cột cần, lọc sớm, tránh hàm bọc cột trong WHERE (to_char(date) = ... làm mất index).
-- 4) Bảng rất lớn: partition theo tháng, hoặc bảng tổng hợp sẵn (mart).
-- Đo trên repo này: sao kê 1 tài khoản/1 tháng trên fact_transactions (1.056.320 dòng)
--   không index (account_id, transaction_date): Gather Merge + Parallel Seq Scan, ~46-52 ms
--   có index fact_transactions_account_date (dbt post_hook): Index Scan, ~0,06-0,10 ms (đo 2026-11-12, Postgres 16 Docker)
explain (analyze, costs off, timing off, summary off)
select transaction_date, direction, amount, balance_after
from core.fact_transactions
where account_id = 2378
  and transaction_date >= '1998-06-01' and transaction_date < '1998-07-01'
order by transaction_date;
