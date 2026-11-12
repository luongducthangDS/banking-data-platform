select
    disp_id::int    as disp_id,
    client_id::int  as client_id,
    account_id::int as account_id,
    lower(type)     as role   -- owner | disponent (may operate the account, cannot own cards/loans)
from {{ source('raw', 'dispositions') }}
