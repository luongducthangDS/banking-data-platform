select
    account_id::int  as account_id,
    district_id::int as district_id,
    case frequency
        when 'POPLATEK MESICNE'   then 'monthly'
        when 'POPLATEK TYDNE'     then 'weekly'
        when 'POPLATEK PO OBRATU' then 'after_transaction'
    end              as statement_frequency,
    {{ yymmdd('date') }} as opened_date
from {{ source('raw', 'accounts') }}
