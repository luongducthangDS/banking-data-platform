select
    card_id::int          as card_id,
    disp_id::int          as disp_id,
    type                  as card_type,   -- junior | classic | gold
    {{ yymmdd('issued') }} as issued_date
from {{ source('raw', 'cards') }}
