-- Q: Khi nào dùng ROW_NUMBER, RANK, DENSE_RANK?
-- ROW_NUMBER: luôn 1,2,3 (không trùng) -> lấy đúng 1 dòng mỗi nhóm, khử trùng.
-- RANK: đồng hạng cùng số, bỏ số sau (1,1,3) -> xếp hạng thi đấu.
-- DENSE_RANK: đồng hạng cùng số, không bỏ số (1,1,2) -> "top N giá trị khác nhau".
-- Bài: xếp hạng quận trong mỗi vùng theo số khoản vay.
select region, district_name, n_loans,
       row_number() over w as row_number,
       rank()       over w as rank,
       dense_rank() over w as dense_rank
from marts.mart_district_kpi
window w as (partition by region order by n_loans desc)
order by region, n_loans desc;
