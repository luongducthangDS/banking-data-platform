select
    order_id::int             as order_id,
    account_id::int           as account_id,
    {{ blank_null('bank_to') }}    as bank_to,
    {{ blank_null('account_to') }} as account_to,
    amount::numeric(14, 2)    as amount,
    case {{ blank_null('k_symbol') }}
        when 'SIPO'     then 'household'
        when 'UVER'     then 'loan_payment'
        when 'POJISTNE' then 'insurance'
        when 'LEASING'  then 'leasing'
    end                       as purpose
from {{ source('raw', 'standing_orders') }}
