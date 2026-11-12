select account_id, client_id, role from {{ ref('stg_dispositions') }}
