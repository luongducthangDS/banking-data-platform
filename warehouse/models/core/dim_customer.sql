with c as (select * from {{ ref('stg_clients') }})
select
    c.client_id,
    c.gender,
    c.birth_date,
    date_part('year', age('{{ var("as_of_date") }}'::date, c.birth_date))::int as age_at_as_of,
    case
        when age('{{ var("as_of_date") }}'::date, c.birth_date) < interval '25 years' then '<25'
        when age('{{ var("as_of_date") }}'::date, c.birth_date) < interval '35 years' then '25-34'
        when age('{{ var("as_of_date") }}'::date, c.birth_date) < interval '50 years' then '35-49'
        when age('{{ var("as_of_date") }}'::date, c.birth_date) < interval '65 years' then '50-64'
        else '65+'
    end                                                as age_band,
    c.district_id,
    d.district_name,
    d.region
from c
left join {{ ref('stg_districts') }} d using (district_id)
