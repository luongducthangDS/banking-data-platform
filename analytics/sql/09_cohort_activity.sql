-- Q: Cohort: khách mở tài khoản năm nào thì năm 1998 còn hoạt động / số dư ra sao?
select extract(year from a.opened_date)::int                          as cohort_year,
       count(*)                                                       as accounts,
       round(avg((m.n_customer_transactions > 0)::int), 3)            as active_dec_1998,
       round(avg(m.end_balance))                                      as avg_balance_dec_1998,
       round(avg(c.is_churn_risk::int), 3)                            as churn_risk_rate
from core.dim_account a
join marts.mart_account_monthly m on m.account_id = a.account_id and m.month_start = '1998-12-01'
join marts.mart_customer_360 c on c.account_id = a.account_id
group by 1
order by 1;
