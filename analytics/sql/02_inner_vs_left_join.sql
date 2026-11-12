-- Q: INNER JOIN và LEFT JOIN khác nhau thế nào?
-- INNER chỉ giữ dòng khớp ở cả hai bảng; LEFT giữ mọi dòng bảng trái, cột bảng phải là NULL khi không khớp.
-- LEFT JOIN + WHERE right.key IS NULL = anti-join ("có A mà không có B").
-- Bài: bao nhiêu tài khoản có/không có khoản vay; và khách có thẻ nhưng chưa vay (đối tượng bán chéo vay).
select
    (select count(*) from core.dim_account a join core.fact_loans l using (account_id))      as accounts_inner_join_loans,
    (select count(*) from core.dim_account a left join core.fact_loans l using (account_id)) as accounts_left_join_loans,
    (select count(*)
       from core.fact_cards c
       left join core.fact_loans l using (account_id)
      where l.loan_id is null)                                                               as card_holders_without_loan;
