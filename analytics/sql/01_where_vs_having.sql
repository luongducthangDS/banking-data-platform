-- Q: WHERE khác HAVING thế nào?
-- WHERE lọc DÒNG trước khi gom nhóm (không dùng được hàm tổng hợp); HAVING lọc NHÓM sau GROUP BY.
-- Bài: các quận ở Moravia có hơn 100 tài khoản, kèm tỷ lệ tài khoản có thẻ.
select d.district_name,
       count(*)                                         as accounts,
       round(avg((c.card_type is not null)::int), 3)    as card_rate
from core.dim_account a
join core.dim_district d using (district_id)
left join (select distinct account_id, card_type from core.fact_cards) c using (account_id)
where d.region like '%Moravia'          -- lọc dòng: chỉ vùng Moravia
group by d.district_name
having count(*) > 100                   -- lọc nhóm: chỉ quận đủ lớn
order by accounts desc;
