select
    c.card_id,
    d.account_id,
    d.client_id,
    c.card_type,
    c.issued_date,
    to_char(c.issued_date, 'YYYYMMDD')::int as issued_date_key
from {{ ref('stg_cards') }} c
join {{ ref('stg_dispositions') }} d using (disp_id)
