-- Account x month grid from the opening month to the latest loaded month, so months without activity exist
-- (needed for "active accounts" and month-end balances). Month-end balance = balance after the
-- last transaction of the month, carried forward through months without transactions.
{{ config(post_hook=["create index if not exists mart_account_monthly_idx on {{ this }} (account_id, month_start)"]) }}

with tx as (
    select account_id, date_trunc('month', transaction_date)::date as month_start,
           transaction_id, transaction_date, direction, amount, balance_after, is_customer_initiated
    from {{ ref('fact_transactions') }}
),
-- only months already loaded: during a backfill the warehouse must not show empty future months
months as (
    select distinct month_start from {{ ref('dim_date') }}
    where month_start <= (select date_trunc('month', max(transaction_date)) from tx)
),
grid as (
    select a.account_id, m.month_start
    from {{ ref('dim_account') }} a
    join months m on m.month_start >= date_trunc('month', a.opened_date)
),
agg as (
    select account_id, month_start,
           count(*)                                              as n_transactions,
           count(*) filter (where is_customer_initiated)         as n_customer_transactions,
           coalesce(sum(amount) filter (where direction = 'credit'), 0) as credit_amount,
           coalesce(sum(amount) filter (where direction = 'debit'), 0)  as debit_amount
    from tx group by account_id, month_start
),
last_tx as (   -- ties on the same day are broken by transaction_id (the source has no time of day)
    select account_id, month_start, balance_after
    from (select account_id, month_start, balance_after,
                 row_number() over (partition by account_id, month_start
                                    order by transaction_date desc, transaction_id desc) as rn
          from tx) x
    where rn = 1
),
joined as (
    select g.account_id, g.month_start,
           coalesce(a.n_transactions, 0)          as n_transactions,
           coalesce(a.n_customer_transactions, 0) as n_customer_transactions,
           coalesce(a.credit_amount, 0)           as credit_amount,
           coalesce(a.debit_amount, 0)            as debit_amount,
           l.balance_after,
           count(l.balance_after) over (partition by g.account_id order by g.month_start) as balance_grp
    from grid g
    left join agg a using (account_id, month_start)
    left join last_tx l using (account_id, month_start)
)
select
    account_id,
    month_start,
    to_char(month_start, 'YYYYMMDD')::int as month_key,
    n_transactions,
    n_customer_transactions,
    n_customer_transactions > 0           as is_active,
    credit_amount,
    debit_amount,
    credit_amount - debit_amount          as net_flow,
    first_value(balance_after) over (partition by account_id, balance_grp order by month_start) as end_balance
from joined
