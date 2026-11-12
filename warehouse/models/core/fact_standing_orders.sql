select order_id, account_id, bank_to, account_to, amount, purpose
from {{ ref('stg_standing_orders') }}
