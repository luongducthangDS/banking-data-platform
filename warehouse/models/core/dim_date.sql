select
    to_char(d, 'YYYYMMDD')::int          as date_key,
    d::date                              as date,
    extract(year from d)::int            as year,
    extract(quarter from d)::int         as quarter,
    extract(month from d)::int           as month,
    date_trunc('month', d)::date         as month_start,
    to_char(d, 'YYYY-MM')                as year_month,
    extract(isodow from d)::int          as iso_day_of_week,
    extract(isodow from d) in (6, 7)     as is_weekend
from generate_series('1993-01-01'::date, '1998-12-31'::date, interval '1 day') as d
