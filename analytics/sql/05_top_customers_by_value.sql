-- Q: Tìm khách có tổng giá trị giao dịch cao nhất.
-- Lưu ý khi trả lời: "giá trị" là gì (tổng tiền vào? ra? cả hai?), kỳ nào, có tính giao dịch ngân hàng tự sinh không,
-- và đồng hạng thì sao (DENSE_RANK để không bỏ sót người bằng điểm).
with v as (
    select a.owner_client_id as client_id, sum(t.amount) as value_1998
    from core.fact_transactions t
    join core.dim_account a using (account_id)
    where t.transaction_date >= '1998-01-01' and t.is_customer_initiated
    group by 1
)
select c.client_id, c.gender, c.age_band, c.region, v.value_1998,
       dense_rank() over (order by v.value_1998 desc) as rnk
from v join core.dim_customer c using (client_id)
order by v.value_1998 desc
limit 10;
