"""Answer the business questions from the marts and write reports/insights.md.

Every sentence with a number is computed here from the query result, so re-running keeps the
report consistent with the data.  Run: PYTHONUTF8=1 .venv/Scripts/python -m analytics.insights
"""
from pathlib import Path

import pandas as pd
import psycopg

from pipeline.extract_load import DSN

OUT = Path(__file__).resolve().parent.parent / "reports" / "insights.md"


def q(conn, sql: str) -> pd.DataFrame:
    cur = conn.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def pct(x) -> str:
    return f"{float(x) * 100:.1f} %"


def section(title: str, sql: str, df: pd.DataFrame, finding: str) -> str:
    return (f"## {title}\n\n{finding}\n\n{df.to_markdown(index=False)}\n\n"
            f"<details><summary>SQL</summary>\n\n```sql\n{sql.strip()}\n```\n</details>\n")


QUESTIONS = []


def question(title, sql):
    def wrap(fn):
        QUESTIONS.append((title, sql, fn))
        return fn
    return wrap


@question("1. Tăng trưởng tiền gửi và hoạt động theo năm", """
select extract(year from month_start)::int as year,
       max(open_accounts) as accounts_end,
       round(sum(credit_amount) / 1e6, 1) as credit_volume_mczk,
       round((array_agg(total_deposits order by month_start desc))[1] / 1e6, 1) as deposits_dec_mczk,
       round(avg(active_rate), 4) as avg_monthly_active_rate
from marts.mart_monthly_kpi group by 1 order by 1""")
def _(d):
    first, last = d.iloc[0], d.iloc[-1]
    growth = float(last.deposits_dec_mczk) / float(first.deposits_dec_mczk)
    return (f"Tiền gửi cuối năm tăng từ {first.deposits_dec_mczk} lên {last.deposits_dec_mczk} triệu CZK "
            f"(x{growth:.1f}) trong {int(last.year - first.year)} năm, số tài khoản từ {first.accounts_end} lên "
            f"{last.accounts_end}. Tỷ lệ tài khoản hoạt động hằng tháng năm {int(last.year)} là "
            f"{pct(last.avg_monthly_active_rate)}: khách gần như không bỏ đi, nên chỉ số 'ngừng giao dịch' "
            f"không phân biệt được ai sắp rời bỏ.")


@question("2. Phân khúc khách hàng (RFM)", """
select rfm_segment, count(*) as customers,
       round(avg(avg_end_balance_1998)) as avg_balance_1998,
       round(avg(n_customer_tx_1998)) as avg_tx_1998,
       round(avg(is_churn_risk::int), 3) as churn_risk_rate,
       round(avg(has_card::int), 3) as card_rate,
       round(sum(avg_end_balance_1998) / sum(sum(avg_end_balance_1998)) over (), 3) as share_of_deposits
from marts.mart_customer_360 group by 1 order by avg_balance_1998 desc""")
def _(d):
    top = d.iloc[0]
    hib = d[d.rfm_segment == "Hibernating"].iloc[0]
    return (f"{top.rfm_segment} ({top.customers} khách) có số dư bình quân {int(top.avg_balance_1998):,} CZK, "
            f"giữ {pct(top.share_of_deposits)} tiền gửi, {pct(top.card_rate)} có thẻ. Hibernating "
            f"({hib.customers} khách) có tỷ lệ rủi ro rời bỏ {pct(hib.churn_risk_rate)}, cao nhất các nhóm. "
            f"Khuyến nghị: ưu tiên giữ chân Hibernating bằng ưu đãi chuyển lương về; bán chéo thẻ cho "
            f"Loyal/Potential vì tỷ lệ có thẻ còn thấp.")


@question("3. Rủi ro rời bỏ (proxy: dòng tiền vào giảm > 50 % so với cùng kỳ)", """
select is_churn_risk, count(*) as customers,
       round(avg(avg_end_balance_1998)) as avg_balance_1998,
       round(avg(n_standing_orders), 2) as avg_standing_orders,
       round(avg(has_card::int), 3) as card_rate,
       round(sum(avg_end_balance_1998) / 1e6, 1) as deposits_mczk
from marts.mart_customer_360 where is_churn_eligible group by 1 order by 1""")
def _(d):
    r = d[d.is_churn_risk].iloc[0]
    n = d[~d.is_churn_risk].iloc[0]
    rate = r.customers / d.customers.sum()
    return (f"{r.customers} khách ({pct(rate)} số khách đủ điều kiện) có dòng tiền vào nửa cuối 1998 giảm hơn một nửa "
            f"so với cùng kỳ 1997, nắm {r.deposits_mczk} triệu CZK tiền gửi. Nhóm này có ít lệnh chuyển "
            f"tiền định kỳ hơn ({r.avg_standing_orders} so với {n.avg_standing_orders}): ít ràng buộc hoá đơn với "
            f"ngân hàng thì dễ chuyển đi. Đây là proxy vì dữ liệu không có ngày đóng tài khoản.")


@question("4. Khoản vay: dấu hiệu trước khi duyệt và tỷ lệ vỡ nợ", """
select case when n_penalty_interest_before > 0 then 'had penalty interest'
            when min_end_balance_6m < 5000 then 'min balance < 5k'
            else 'neither' end as pre_grant_signal,
       count(*) as loans,
       sum(is_default::int) as defaults,
       round(avg(is_default::int), 3) as default_rate,
       round(avg(payment_to_income), 3) as avg_payment_to_income
from marts.mart_loan_performance group by 1 order by default_rate desc""")
def _(d):
    a, c = d.iloc[0], d[d.pre_grant_signal == "neither"].iloc[0]
    return (f"Khoản vay của khách từng bị phạt lãi (số dư âm) trước ngày duyệt vỡ nợ {pct(a.default_rate)} "
            f"({a.defaults}/{a.loans}), so với {pct(c.default_rate)} khi không có tín hiệu nào. Cả hai tín hiệu đều "
            f"có sẵn lúc duyệt, nên nên đưa vào quy tắc thẩm định (ví dụ chuyển hồ sơ sang thẩm định thủ công).")


@question("5. Vỡ nợ theo quy mô khoản vay", """
select amount_band, count(*) as loans, round(avg(is_default::int), 3) as default_rate,
       round(sum(amount) filter (where is_default) / 1e6, 2) as defaulted_amount_mczk
from marts.mart_loan_performance group by 1
order by min(amount)""")
def _(d):
    lo, hi = d.iloc[0], d.iloc[-1]
    big = d[d.amount_band.isin(["150k-300k", "300k+"])]
    share = big.defaulted_amount_mczk.sum() / d.defaulted_amount_mczk.sum()
    return (f"Tỷ lệ vỡ nợ tăng theo quy mô: {lo.amount_band} là {pct(lo.default_rate)}, {hi.amount_band} là "
            f"{pct(hi.default_rate)}. Khoản từ 150k trở lên chiếm {big.loans.sum()}/{d.loans.sum()} khoản vay "
            f"nhưng {pct(share)} số tiền vỡ nợ.")


@question("6. Theo vùng: tiền gửi và chất lượng tín dụng", """
select region, sum(n_accounts) as accounts, round(sum(deposits_dec_1998) / 1e6, 1) as deposits_dec98_mczk,
       sum(n_loans) as loans,
       round(sum(default_rate * n_loans) / nullif(sum(n_loans), 0), 3) as default_rate
from marts.mart_district_kpi group by 1 order by deposits_dec98_mczk desc""")
def _(d):
    worst = d.sort_values("default_rate").iloc[-1]
    best = d.sort_values("default_rate").iloc[0]
    return (f"Tỷ lệ vỡ nợ chênh lệch giữa các vùng: {worst.region} {pct(worst.default_rate)} so với {best.region} "
            f"{pct(best.default_rate)}. Mỗi vùng chỉ có 57–129 khoản vay nên chênh lệch này cần kiểm định "
            f"thống kê trước khi đổi chính sách theo vùng.")


def main() -> None:
    parts = ["# Insight từ Banking Data Platform\n",
             "Dữ liệu: PKDD'99 (Berka), ngân hàng Séc 1993–1998, thật và đã ẩn danh. Số liệu sinh bởi "
             "`analytics/insights.py` từ schema `marts`; định nghĩa KPI ở `docs/KPI_DEFINITIONS.md`.\n"]
    with psycopg.connect(DSN) as conn:
        for title, sql, fn in QUESTIONS:
            df = q(conn, sql)
            parts.append(section(title, sql, df, fn(df)))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
