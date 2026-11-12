-- One row per month. Definitions: docs/KPI_DEFINITIONS.md.
with am as (
    select month_start,
           count(*)                                   as open_accounts,
           count(*) filter (where is_active)          as active_accounts,
           sum(n_transactions)                        as n_transactions,
           sum(n_customer_transactions)               as n_customer_transactions,
           sum(credit_amount)                         as credit_amount,
           sum(debit_amount)                          as debit_amount,
           sum(coalesce(end_balance, 0))              as total_deposits
    from {{ ref('mart_account_monthly') }}
    group by month_start
),
new_accounts as (
    select date_trunc('month', opened_date)::date as month_start, count(*) as new_accounts
    from {{ ref('dim_account') }} group by 1
),
new_loans as (
    select date_trunc('month', granted_date)::date as month_start,
           count(*) as new_loans, sum(amount) as new_loan_amount
    from {{ ref('fact_loans') }} group by 1
),
new_cards as (
    select date_trunc('month', issued_date)::date as month_start, count(*) as new_cards
    from {{ ref('fact_cards') }} group by 1
)
select
    am.month_start,
    to_char(am.month_start, 'YYYY-MM')                                  as year_month,
    am.open_accounts,
    am.active_accounts,
    round(am.active_accounts::numeric / nullif(am.open_accounts, 0), 4) as active_rate,
    am.n_transactions,
    am.n_customer_transactions,
    am.credit_amount,
    am.debit_amount,
    am.credit_amount - am.debit_amount                                  as net_flow,
    am.total_deposits,
    coalesce(na.new_accounts, 0)                                        as new_accounts,
    coalesce(nl.new_loans, 0)                                           as new_loans,
    coalesce(nl.new_loan_amount, 0)                                     as new_loan_amount,
    coalesce(nc.new_cards, 0)                                           as new_cards
from am
left join new_accounts na using (month_start)
left join new_loans nl using (month_start)
left join new_cards nc using (month_start)
