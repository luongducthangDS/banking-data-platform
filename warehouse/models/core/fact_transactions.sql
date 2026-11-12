-- Incremental: each run only processes raw rows loaded after the latest loaded_at already here.
-- Raw rows are insert-only (ON CONFLICT DO NOTHING), so this never misses or duplicates a row;
-- unique_key makes a re-run of the same batch a merge, not an append.
{{ config(
    materialized='incremental',
    unique_key='transaction_id',
    incremental_strategy='merge',
    post_hook=[
      "create unique index if not exists fact_transactions_pk on {{ this }} (transaction_id)",
      "create index if not exists fact_transactions_account_date on {{ this }} (account_id, transaction_date)",
      "create index if not exists fact_transactions_date_key on {{ this }} (date_key)",
      "analyze {{ this }}"
    ]
) }}

select
    t.transaction_id,
    t.account_id,
    to_char(t.transaction_date, 'YYYYMMDD')::int as date_key,
    t.transaction_date,
    t.direction,
    t.operation,
    t.purpose,
    t.amount,
    t.signed_amount,
    t.balance_after,
    t.partner_bank,
    t.partner_account,
    t.is_customer_initiated,
    t.loaded_at
from {{ ref('stg_transactions') }} t
{% if is_incremental() %}
where t.loaded_at > (select coalesce(max(loaded_at), '-infinity') from {{ this }})
{% endif %}
