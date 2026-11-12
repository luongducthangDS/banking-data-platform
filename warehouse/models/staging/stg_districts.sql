-- Columns A1..A16 per the PKDD'99 description; '?' marks missing 1995 figures.
select
    a1::int                          as district_id,
    a2                               as district_name,
    a3                               as region,
    a4::int                          as inhabitants,
    a9::int                          as n_cities,
    a10::numeric(5, 1)               as urban_ratio_pct,
    a11::int                         as avg_salary,
    nullif(a12, '?')::numeric(5, 2)  as unemployment_rate_95,
    a13::numeric(5, 2)               as unemployment_rate_96,
    a14::int                         as entrepreneurs_per_1000,
    nullif(a15, '?')::int            as crimes_95,
    a16::int                         as crimes_96
from {{ source('raw', 'districts') }}
