select
    loan_id::int                 as loan_id,
    account_id::int              as account_id,
    {{ yymmdd('date') }}         as granted_date,
    amount::numeric(14, 2)       as amount,
    duration::int                as duration_months,
    payments::numeric(14, 2)     as monthly_payment,
    status                       as status_code,
    case status
        when 'A' then 'finished_ok'
        when 'B' then 'finished_unpaid'
        when 'C' then 'running_ok'
        when 'D' then 'running_in_debt'
    end                          as status,
    status in ('B', 'D')         as is_default
from {{ source('raw', 'loans') }}
