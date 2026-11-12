-- One row per district (branch catchment): customers, deposits, activity, lending, socio-economics.
with acc as (
    select a.district_id, count(*) as n_accounts
    from {{ ref('dim_account') }} a group by 1
),
dec98 as (
    select a.district_id,
           sum(m.end_balance)                     as deposits_dec_1998,
           count(*) filter (where m.is_active)    as active_accounts_dec_1998
    from {{ ref('mart_account_monthly') }} m
    join {{ ref('dim_account') }} a using (account_id)
    where m.month_start = '1998-12-01'
    group by 1
),
vol as (
    select a.district_id, sum(t.amount) as transaction_volume_1998
    from {{ ref('fact_transactions') }} t
    join {{ ref('dim_account') }} a using (account_id)
    where t.transaction_date >= '1998-01-01'
    group by 1
),
loans as (
    select a.district_id, count(*) as n_loans, sum(l.amount) as loan_amount,
           avg(l.is_default::int) as default_rate
    from {{ ref('fact_loans') }} l
    join {{ ref('dim_account') }} a using (account_id)
    group by 1
)
select
    d.district_id, d.district_name, d.region, d.inhabitants, d.avg_salary,
    d.unemployment_rate_96, d.urban_ratio_pct,
    coalesce(acc.n_accounts, 0)                     as n_accounts,
    coalesce(dec98.active_accounts_dec_1998, 0)     as active_accounts_dec_1998,
    coalesce(dec98.deposits_dec_1998, 0)            as deposits_dec_1998,
    coalesce(vol.transaction_volume_1998, 0)        as transaction_volume_1998,
    coalesce(loans.n_loans, 0)                      as n_loans,
    coalesce(loans.loan_amount, 0)                  as loan_amount,
    round(loans.default_rate, 4)                    as default_rate
from {{ ref('dim_district') }} d
left join acc using (district_id)
left join dec98 using (district_id)
left join vol using (district_id)
left join loans using (district_id)
