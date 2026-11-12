-- One row per account. Every account has exactly one owner (tested in core.yml).
with owners as (
    select account_id, client_id as owner_client_id from {{ ref('stg_dispositions') }} where role = 'owner'
),
disponents as (
    select account_id, count(*) as n_disponents from {{ ref('stg_dispositions') }}
    where role = 'disponent' group by account_id
)
select
    a.account_id,
    a.district_id,
    d.region,
    a.statement_frequency,
    a.opened_date,
    to_char(a.opened_date, 'YYYYMMDD')::int as opened_date_key,
    o.owner_client_id,
    coalesce(dp.n_disponents, 0) > 0        as has_disponent
from {{ ref('stg_accounts') }} a
join owners o using (account_id)
left join disponents dp using (account_id)
left join {{ ref('stg_districts') }} d using (district_id)
