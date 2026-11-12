-- birth_number is YYMMDD for men and YY(MM+50)DD for women (PKDD'99 data description).
with src as (
    select client_id::int as client_id, district_id::int as district_id,
           substr(birth_number, 1, 2)::int as yy, substr(birth_number, 3, 2)::int as mm,
           substr(birth_number, 5, 2)::int as dd
    from {{ source('raw', 'clients') }}
)
select
    client_id,
    district_id,
    case when mm > 50 then 'F' else 'M' end                          as gender,
    make_date(1900 + yy, case when mm > 50 then mm - 50 else mm end, dd) as birth_date
from src
