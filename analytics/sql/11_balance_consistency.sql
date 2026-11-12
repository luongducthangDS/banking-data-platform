-- Q: Kiểm tra số dư có khớp với giao dịch không (window + tolerance).
-- Nguồn không có giờ giao dịch, nên thứ tự trong cùng ngày không biết được: so theo NGÀY.
-- Neo vào ngày trước có đúng 1 giao dịch (biết chắc số dư cuối ngày đó), rồi kiểm:
--   số dư đầu + tổng tiền có dấu của ngày ≈ một trong các balance_after của ngày (sai số làm tròn 0,10 CZK
--   có thật ở giao dịch cộng lãi). Đây cũng là luật consistency trong dq/.
with d as (
    select account_id, transaction_date, sum(signed_amount) as day_net, count(*) as n,
           array_agg(balance_after) as balances
    from core.fact_transactions group by 1, 2
),
l as (
    select *, lag(balances[1]) over w as prev_eod, lag(n) over w as prev_n
    from d window w as (partition by account_id order by transaction_date)
)
select count(*) filter (where prev_n = 1)                                         as checkable_days,
       count(*) filter (where prev_n = 1 and not exists (
           select 1 from unnest(balances) b where abs(prev_eod + day_net - b) <= 0.10)) as inconsistent_days
from l;
