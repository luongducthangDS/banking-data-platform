-- Typed transactions with Czech codes translated. Mapping from the PKDD'99 data description;
-- type 'VYBER' (16,666 rows) is undocumented and behaves as a cash withdrawal (debit).
with src as (select * from {{ source('raw', 'transactions') }})

select
    trans_id::bigint                                   as transaction_id,
    account_id::int                                    as account_id,
    {{ yymmdd('date') }}                               as transaction_date,
    type                                               as type_code,
    case when type = 'PRIJEM' then 'credit'
         when type in ('VYDAJ', 'VYBER') then 'debit' end as direction,
    case operation
        when 'VKLAD'          then 'cash_deposit'
        when 'VYBER'          then 'cash_withdrawal'
        when 'VYBER KARTOU'   then 'card_withdrawal'
        when 'PREVOD Z UCTU'  then 'collection_from_other_bank'
        when 'PREVOD NA UCET' then 'remittance_to_other_bank'
        else case when {{ blank_null('k_symbol') }} = 'UROK' then 'interest_credit' end
    end                                                as operation,
    case {{ blank_null('k_symbol') }}
        when 'POJISTNE'    then 'insurance'
        when 'SLUZBY'      then 'statement_fee'
        when 'UROK'        then 'interest_credited'
        when 'SANKC. UROK' then 'penalty_interest'
        when 'SIPO'        then 'household'
        when 'DUCHOD'      then 'pension'
        when 'UVER'        then 'loan_payment'
    end                                                as purpose,
    amount::numeric(14, 2)                             as amount,
    case when type = 'PRIJEM' then 1 else -1 end * amount::numeric(14, 2) as signed_amount,
    balance::numeric(14, 2)                            as balance_after,
    {{ blank_null('bank') }}                           as partner_bank,
    {{ blank_null('account') }}                        as partner_account,
    -- bank-generated rows (interest, statement fees, penalty interest) are not customer activity
    coalesce({{ blank_null('k_symbol') }}, '') not in ('UROK', 'SLUZBY', 'SANKC. UROK') as is_customer_initiated,
    _loaded_at                                         as loaded_at
from src
