-- One row per loan with borrower profile and behaviour in the 6 months BEFORE the grant date
-- (only information available at decision time, so it can be used to study default risk).
with pre as (
    select l.loan_id,
           avg(m.end_balance)   as avg_end_balance_6m,
           min(m.end_balance)   as min_end_balance_6m,
           avg(m.credit_amount) as avg_monthly_credit_6m
    from {{ ref('fact_loans') }} l
    join {{ ref('mart_account_monthly') }} m
      on m.account_id = l.account_id
     and m.month_start >= (date_trunc('month', l.granted_date) - interval '6 months')
     and m.month_start <  date_trunc('month', l.granted_date)
    group by l.loan_id
),
penalties as (
    select l.loan_id, count(t.transaction_id) as n_penalty_interest_before
    from {{ ref('fact_loans') }} l
    left join {{ ref('fact_transactions') }} t
      on t.account_id = l.account_id and t.purpose = 'penalty_interest' and t.transaction_date < l.granted_date
    group by l.loan_id
),
cards as (select distinct account_id from {{ ref('fact_cards') }})
select
    l.loan_id,
    l.account_id,
    l.client_id,
    l.granted_date,
    extract(year from l.granted_date)::int                      as granted_year,
    l.amount,
    case when l.amount < 50000 then '<50k'
         when l.amount < 150000 then '50k-150k'
         when l.amount < 300000 then '150k-300k'
         else '300k+' end                                        as amount_band,
    l.duration_months,
    l.monthly_payment,
    l.status_code,
    l.status,
    l.is_default,
    c.gender,
    c.age_band,
    d.region,
    d.district_name,
    d.avg_salary                                                 as district_avg_salary,
    d.unemployment_rate_96                                       as district_unemployment_96,
    cards.account_id is not null                                 as has_card,
    round(p.avg_end_balance_6m, 2)                               as avg_end_balance_6m,
    p.min_end_balance_6m,
    round(p.avg_monthly_credit_6m, 2)                            as avg_monthly_credit_6m,
    round(l.monthly_payment / nullif(p.avg_monthly_credit_6m, 0), 4) as payment_to_income,
    pen.n_penalty_interest_before
from {{ ref('fact_loans') }} l
join {{ ref('dim_customer') }} c using (client_id)
join {{ ref('dim_account') }} a using (account_id)
join {{ ref('dim_district') }} d on d.district_id = a.district_id
left join pre p using (loan_id)
left join penalties pen using (loan_id)
left join cards using (account_id)
