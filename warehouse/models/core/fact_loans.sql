select
    l.loan_id,
    l.account_id,
    a.owner_client_id                              as client_id,
    to_char(l.granted_date, 'YYYYMMDD')::int       as granted_date_key,
    l.granted_date,
    l.amount,
    l.duration_months,
    l.monthly_payment,
    l.status_code,
    l.status,
    l.is_default
from {{ ref('stg_loans') }} l
join {{ ref('dim_account') }} a using (account_id)
