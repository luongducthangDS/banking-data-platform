-- One row per account owner (in Berka each client is on exactly one account).
-- The source has no account closures, so churn is a PROXY (docs/KPI_DEFINITIONS.md):
--   is_dormant    : no customer-initiated transaction in the last 6 months
--   is_churn_risk : credit inflow Jul-Dec 1998 < 50 % of Jul-Dec 1997 (year over year, removes seasonality),
--                   only for accounts opened before 1997-07-01
-- RFM: R = days since last customer-initiated transaction, F = customer-initiated transactions in 1998,
--      M = average month-end balance in 1998 (deposit value matters more to a bank than spend).
{% set as_of = var('as_of_date') %}
with tx as (
    select account_id,
           max(transaction_date) filter (where is_customer_initiated)                       as last_customer_tx,
           count(*) filter (where is_customer_initiated and transaction_date >= '1998-01-01') as n_customer_tx_1998,
           sum(amount) filter (where direction = 'credit' and transaction_date >= '1998-07-01') as credit_h2_1998,
           sum(amount) filter (where direction = 'credit' and transaction_date >= '1997-07-01'
                                 and transaction_date < '1998-01-01')                            as credit_h2_1997,
           count(*) filter (where purpose = 'penalty_interest')                                 as n_penalty_interest,
           min(balance_after)                                                                   as min_balance_ever
    from {{ ref('fact_transactions') }}
    group by account_id
),
bal as (
    select account_id, avg(end_balance) as avg_end_balance_1998,
           avg(credit_amount) as avg_monthly_credit_1998
    from {{ ref('mart_account_monthly') }}
    where month_start >= '1998-01-01'
    group by account_id
),
loan as (select account_id, status as loan_status, is_default as loan_default, amount as loan_amount
         from {{ ref('fact_loans') }}),
card as (select account_id, max(card_type) as card_type from {{ ref('fact_cards') }} group by account_id),
orders as (select account_id, count(*) as n_standing_orders from {{ ref('fact_standing_orders') }} group by account_id),
base as (
    select
        a.account_id, a.owner_client_id as client_id,
        c.gender, c.age_band, c.district_name, a.region, a.statement_frequency, a.opened_date,
        (date_part('year', age('{{ as_of }}'::date, a.opened_date)) * 12
         + date_part('month', age('{{ as_of }}'::date, a.opened_date)))::int as tenure_months,
        a.has_disponent,
        ('{{ as_of }}'::date - tx.last_customer_tx)                     as recency_days,
        coalesce(tx.n_customer_tx_1998, 0)                              as n_customer_tx_1998,
        round(bal.avg_end_balance_1998, 2)                              as avg_end_balance_1998,
        round(bal.avg_monthly_credit_1998, 2)                           as avg_monthly_credit_1998,
        tx.min_balance_ever,
        tx.n_penalty_interest,
        loan.account_id is not null                                     as has_loan,
        loan.loan_status, loan.loan_default, loan.loan_amount,
        card.card_type is not null                                      as has_card,
        card.card_type,
        coalesce(orders.n_standing_orders, 0)                           as n_standing_orders,
        tx.last_customer_tx is null or tx.last_customer_tx < '1998-07-01' as is_dormant,
        a.opened_date < '1997-07-01'                                    as is_churn_eligible,
        a.opened_date < '1997-07-01' and coalesce(tx.credit_h2_1997, 0) > 0
          and coalesce(tx.credit_h2_1998, 0) < 0.5 * tx.credit_h2_1997  as is_churn_risk
    from {{ ref('dim_account') }} a
    join {{ ref('dim_customer') }} c on c.client_id = a.owner_client_id
    left join tx using (account_id)
    left join bal using (account_id)
    left join loan using (account_id)
    left join card using (account_id)
    left join orders using (account_id)
),
scored as (
    select *,
           ntile(5) over (order by recency_days desc nulls first, account_id)  as r_score,
           ntile(5) over (order by n_customer_tx_1998, account_id)             as f_score,
           ntile(5) over (order by avg_end_balance_1998 nulls first, account_id) as m_score
    from base
)
select *,
       case
           when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
           when f_score >= 4 and m_score >= 3                  then 'Loyal'
           when r_score <= 2 and f_score >= 3                  then 'At risk'
           when r_score <= 2 and f_score <= 2                  then 'Hibernating'
           when r_score >= 3 and f_score <= 3                  then 'Potential'
           else 'Needs attention'
       end as rfm_segment
from scored
