-- Q: Tăng trưởng tiền gửi so với tháng trước và cùng kỳ năm trước (LAG).
select year_month,
       total_deposits,
       round(total_deposits / lag(total_deposits) over w - 1, 4)      as mom_growth,
       round(total_deposits / lag(total_deposits, 12) over w - 1, 4)  as yoy_growth,
       round(avg(credit_amount) over (order by month_start rows between 2 preceding and current row), 2) as credit_3m_avg
from marts.mart_monthly_kpi
window w as (order by month_start)
order by month_start desc
limit 12;
