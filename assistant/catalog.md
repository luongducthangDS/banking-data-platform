Bank: anonymised Czech retail bank (PKDD'99). Currency CZK. Data covers 1993-01-01 .. 1998-12-31.
"Now", "this month", "last month", "this year" refer to the end of the data: latest month = 1998-12, latest year = 1998,
previous month = 1998-11, previous year = 1997. Each client owns exactly one account (customer = account owner).

marts.mart_monthly_kpi - one row per month (month_start date, year_month 'YYYY-MM'): open_accounts, active_accounts,
  active_rate (0-1), n_transactions, n_customer_transactions, credit_amount (money in), debit_amount (money out),
  net_flow, total_deposits (sum of month-end balances), new_accounts, new_loans, new_loan_amount, new_cards.
marts.mart_account_monthly - one row per account per month: n_transactions, n_customer_transactions, is_active,
  credit_amount, debit_amount, net_flow, end_balance (month-end balance).
marts.mart_customer_360 - one row per customer/account: gender ('F'/'M'), age_band ('<25','25-34','35-49','50-64','65+'),
  district_name, region, statement_frequency, opened_date, tenure_months, recency_days, n_customer_tx_1998,
  avg_end_balance_1998, avg_monthly_credit_1998, has_loan, loan_status, loan_default, loan_amount, has_card,
  card_type ('junior','classic','gold' or null), n_standing_orders, is_dormant, is_churn_eligible, is_churn_risk,
  r_score, f_score, m_score (1-5), rfm_segment ('Champions','Loyal','At risk','Hibernating','Potential','Needs attention').
marts.mart_loan_performance - one row per loan: granted_date, granted_year, amount, amount_band, duration_months,
  monthly_payment, status ('finished_ok','finished_unpaid','running_ok','running_in_debt'), is_default (status B or D),
  gender, age_band, region, district_name, district_avg_salary, district_unemployment_96, has_card,
  avg_end_balance_6m, min_end_balance_6m, avg_monthly_credit_6m, payment_to_income, n_penalty_interest_before.
marts.mart_district_kpi - one row per district: district_name, region, inhabitants, avg_salary, unemployment_rate_96,
  n_accounts, active_accounts_dec_1998, deposits_dec_1998, transaction_volume_1998, n_loans, loan_amount, default_rate.
core.fact_transactions - one row per transaction (1,056,320 rows): transaction_id, account_id, date_key, transaction_date,
  direction ('credit','debit'), operation ('cash_deposit','cash_withdrawal','card_withdrawal','collection_from_other_bank',
  'remittance_to_other_bank','interest_credit'), purpose ('insurance','statement_fee','interest_credited','penalty_interest',
  'household','pension','loan_payment' or null), amount (always positive), signed_amount, balance_after,
  is_customer_initiated (false for interest, fees and penalty interest).
core.dim_account - account_id, district_id, region, statement_frequency, opened_date, owner_client_id, has_disponent.
core.dim_customer - client_id, gender, birth_date, age_at_as_of, age_band, district_id, district_name, region.
core.dim_district - district_id, district_name, region, inhabitants, avg_salary, unemployment_rate_95/96, crimes_95/96.
core.dim_date - date_key, date, year, quarter, month, month_start, year_month, iso_day_of_week, is_weekend.
core.fact_loans - loan_id, account_id, client_id, granted_date, amount, duration_months, monthly_payment, status, is_default.
core.fact_cards - card_id, account_id, client_id, card_type, issued_date.
core.fact_standing_orders - order_id, account_id, bank_to, account_to, amount, purpose.
