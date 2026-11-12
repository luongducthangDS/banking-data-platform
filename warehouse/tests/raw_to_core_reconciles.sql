-- Row count and total amount in core must equal raw (no row lost or duplicated by ELT).
with r as (select count(*) as n, sum(amount::numeric) as amt from {{ source('raw', 'transactions') }}),
     f as (select count(*) as n, sum(amount) as amt from {{ ref('fact_transactions') }})
select r.n as raw_rows, f.n as core_rows, r.amt as raw_amount, f.amt as core_amount
from r, f
where r.n <> f.n or r.amt <> f.amt
