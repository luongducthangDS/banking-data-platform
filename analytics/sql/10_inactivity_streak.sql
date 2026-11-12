-- Q (gaps and islands): chuỗi tháng không hoạt động dài nhất của mỗi tài khoản.
-- Mẹo: trong một chuỗi liên tiếp, (số thứ tự tháng) - row_number() là hằng số -> dùng làm khoá nhóm.
with inactive as (
    select account_id, month_start,
           (extract(year from month_start) * 12 + extract(month from month_start))::int
             - row_number() over (partition by account_id order by month_start) as grp
    from marts.mart_account_monthly
    where not is_active
),
streaks as (
    select account_id, min(month_start) as from_month, max(month_start) as to_month, count(*) as months
    from inactive group by account_id, grp
)
select account_id, from_month, to_month, months
from (select *, row_number() over (partition by account_id order by months desc, from_month) as rn from streaks) s
where rn = 1
order by months desc, account_id
limit 10;
