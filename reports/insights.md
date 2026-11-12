# Insight từ Banking Data Platform

Dữ liệu: PKDD'99 (Berka), ngân hàng Séc 1993–1998, thật và đã ẩn danh. Số liệu sinh bởi `analytics/insights.py` từ schema `marts`; định nghĩa KPI ở `docs/KPI_DEFINITIONS.md`.

## 1. Tăng trưởng tiền gửi và hoạt động theo năm

Tiền gửi cuối năm tăng từ 37.1 lên 197.1 triệu CZK (x5.3) trong 5 năm, số tài khoản từ 1139 lên 4500. Tỷ lệ tài khoản hoạt động hằng tháng năm 1998 là 99.1 %: khách gần như không bỏ đi, nên chỉ số 'ngừng giao dịch' không phân biệt được ai sắp rời bỏ.

|   year |   accounts_end |   credit_volume_mczk |   deposits_dec_mczk |   avg_monthly_active_rate |
|-------:|---------------:|---------------------:|--------------------:|--------------------------:|
|   1993 |           1139 |                120.4 |                37.1 |                    0.9995 |
|   1994 |           1578 |                278.5 |                55.3 |                    0.9993 |
|   1995 |           2239 |                396.1 |                80.1 |                    0.9985 |
|   1996 |           3602 |                606.8 |               130.4 |                    0.9962 |
|   1997 |           4500 |                864.7 |               171.3 |                    0.995  |
|   1998 |           4500 |                961   |               197.1 |                    0.9914 |

<details><summary>SQL</summary>

```sql
select extract(year from month_start)::int as year,
       max(open_accounts) as accounts_end,
       round(sum(credit_amount) / 1e6, 1) as credit_volume_mczk,
       round((array_agg(total_deposits order by month_start desc))[1] / 1e6, 1) as deposits_dec_mczk,
       round(avg(active_rate), 4) as avg_monthly_active_rate
from marts.mart_monthly_kpi group by 1 order by 1
```
</details>

## 2. Phân khúc khách hàng (RFM)

Champions (536 khách) có số dư bình quân 60,556 CZK, giữ 19.2 % tiền gửi, 40.3 % có thẻ. Hibernating (849 khách) có tỷ lệ rủi ro rời bỏ 11.8 %, cao nhất các nhóm. Khuyến nghị: ưu tiên giữ chân Hibernating bằng ưu đãi chuyển lương về; bán chéo thẻ cho Loyal/Potential vì tỷ lệ có thẻ còn thấp.

| rfm_segment     |   customers |   avg_balance_1998 |   avg_tx_1998 |   churn_risk_rate |   card_rate |   share_of_deposits |
|:----------------|------------:|-------------------:|--------------:|------------------:|------------:|--------------------:|
| Champions       |         536 |              60556 |            67 |             0.017 |       0.403 |               0.192 |
| Loyal           |         842 |              47469 |            65 |             0.031 |       0.281 |               0.236 |
| Potential       |        1488 |              34390 |            40 |             0.059 |       0.171 |               0.303 |
| At risk         |         544 |              31279 |            51 |             0.024 |       0.16  |               0.101 |
| Hibernating     |         849 |              27567 |            32 |             0.118 |       0.112 |               0.138 |
| Needs attention |         241 |              21094 |            62 |             0.017 |       0.008 |               0.03  |

<details><summary>SQL</summary>

```sql
select rfm_segment, count(*) as customers,
       round(avg(avg_end_balance_1998)) as avg_balance_1998,
       round(avg(n_customer_tx_1998)) as avg_tx_1998,
       round(avg(is_churn_risk::int), 3) as churn_risk_rate,
       round(avg(has_card::int), 3) as card_rate,
       round(sum(avg_end_balance_1998) / sum(sum(avg_end_balance_1998)) over (), 3) as share_of_deposits
from marts.mart_customer_360 group by 1 order by avg_balance_1998 desc
```
</details>

## 3. Rủi ro rời bỏ (proxy: dòng tiền vào giảm > 50 % so với cùng kỳ)

240 khách (5.9 % số khách đủ điều kiện) có dòng tiền vào nửa cuối 1998 giảm hơn một nửa so với cùng kỳ 1997, nắm 7.7 triệu CZK tiền gửi. Nhóm này có ít lệnh chuyển tiền định kỳ hơn (0.94 so với 1.47): ít ràng buộc hoá đơn với ngân hàng thì dễ chuyển đi. Đây là proxy vì dữ liệu không có ngày đóng tài khoản.

| is_churn_risk   |   customers |   avg_balance_1998 |   avg_standing_orders |   card_rate |   deposits_mczk |
|:----------------|------------:|-------------------:|----------------------:|------------:|----------------:|
| False           |        3811 |              38250 |                  1.47 |       0.197 |           145.8 |
| True            |         240 |              32286 |                  0.94 |       0.221 |             7.7 |

<details><summary>SQL</summary>

```sql
select is_churn_risk, count(*) as customers,
       round(avg(avg_end_balance_1998)) as avg_balance_1998,
       round(avg(n_standing_orders), 2) as avg_standing_orders,
       round(avg(has_card::int), 3) as card_rate,
       round(sum(avg_end_balance_1998) / 1e6, 1) as deposits_mczk
from marts.mart_customer_360 where is_churn_eligible group by 1 order by 1
```
</details>

## 4. Khoản vay: dấu hiệu trước khi duyệt và tỷ lệ vỡ nợ

Khoản vay của khách từng bị phạt lãi (số dư âm) trước ngày duyệt vỡ nợ 89.7 % (26/29), so với 5.2 % khi không có tín hiệu nào. Cả hai tín hiệu đều có sẵn lúc duyệt, nên nên đưa vào quy tắc thẩm định (ví dụ chuyển hồ sơ sang thẩm định thủ công).

| pre_grant_signal     |   loans |   defaults |   default_rate |   avg_payment_to_income |
|:---------------------|--------:|-----------:|---------------:|------------------------:|
| had penalty interest |      29 |         26 |          0.897 |                   0.25  |
| min balance < 5k     |      78 |         20 |          0.256 |                   0.313 |
| neither              |     575 |         30 |          0.052 |                   0.172 |

<details><summary>SQL</summary>

```sql
select case when n_penalty_interest_before > 0 then 'had penalty interest'
            when min_end_balance_6m < 5000 then 'min balance < 5k'
            else 'neither' end as pre_grant_signal,
       count(*) as loans,
       sum(is_default::int) as defaults,
       round(avg(is_default::int), 3) as default_rate,
       round(avg(payment_to_income), 3) as avg_payment_to_income
from marts.mart_loan_performance group by 1 order by default_rate desc
```
</details>

## 5. Vỡ nợ theo quy mô khoản vay

Tỷ lệ vỡ nợ tăng theo quy mô: <50k là 4.0 %, 300k+ là 20.7 %. Khoản từ 150k trở lên chiếm 287/682 khoản vay nhưng 84.1 % số tiền vỡ nợ.

| amount_band   |   loans |   default_rate |   defaulted_amount_mczk |
|:--------------|--------:|---------------:|------------------------:|
| <50k          |     126 |          0.04  |                    0.18 |
| 50k-150k      |     269 |          0.097 |                    2.29 |
| 150k-300k     |     205 |          0.137 |                    6.39 |
| 300k+         |      82 |          0.207 |                    6.72 |

<details><summary>SQL</summary>

```sql
select amount_band, count(*) as loans, round(avg(is_default::int), 3) as default_rate,
       round(sum(amount) filter (where is_default) / 1e6, 2) as defaulted_amount_mczk
from marts.mart_loan_performance group by 1
order by min(amount)
```
</details>

## 6. Theo vùng: tiền gửi và chất lượng tín dụng

Tỷ lệ vỡ nợ chênh lệch giữa các vùng: west Bohemia 15.8 % so với north Bohemia 1.6 %. Mỗi vùng chỉ có 57–129 khoản vay nên chênh lệch này cần kiểm định thống kê trước khi đổi chính sách theo vùng.

| region          |   accounts |   deposits_dec98_mczk |   loans |   default_rate |
|:----------------|-----------:|----------------------:|--------:|---------------:|
| north Moravia   |        793 |                  35   |     117 |          0.154 |
| south Moravia   |        778 |                  34   |     129 |          0.101 |
| central Bohemia |        574 |                  25.2 |      90 |          0.111 |
| Prague          |        554 |                  24.9 |      84 |          0.083 |
| east Bohemia    |        544 |                  23.7 |      84 |          0.107 |
| north Bohemia   |        457 |                  20.2 |      61 |          0.016 |
| west Bohemia    |        430 |                  18.8 |      57 |          0.158 |
| south Bohemia   |        370 |                  15.5 |      60 |          0.15  |

<details><summary>SQL</summary>

```sql
select region, sum(n_accounts) as accounts, round(sum(deposits_dec_1998) / 1e6, 1) as deposits_dec98_mczk,
       sum(n_loans) as loans,
       round(sum(default_rate * n_loans) / nullif(sum(n_loans), 0), 3) as default_rate
from marts.mart_district_kpi group by 1 order by deposits_dec98_mczk desc
```
</details>
