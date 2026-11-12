-- Q: Thiết kế database quản lý khách hàng ngân hàng (OLTP).
-- Nguyên tắc: chuẩn hoá 3NF, khoá ngoại + CHECK đặt luật ở DB, tiền là numeric (không float),
-- giao dịch là append-only (sửa sai bằng giao dịch đảo, không UPDATE), index theo truy vấn chính.
-- Chạy trong schema tạm và rollback (tests/test_sql_examples.py).
create schema oltp_demo;

create table oltp_demo.customer (
    customer_id   bigint generated always as identity primary key,
    national_id   text not null unique,                      -- CCCD/CMND
    full_name     text not null,
    birth_date    date not null check (birth_date < current_date),
    phone         text,
    created_at    timestamptz not null default now()
);

create table oltp_demo.account (
    account_id    bigint generated always as identity primary key,
    account_no    text not null unique,
    product       text not null check (product in ('current', 'savings', 'loan')),
    currency      char(3) not null default 'VND',
    status        text not null default 'active' check (status in ('active', 'frozen', 'closed')),
    opened_at     timestamptz not null default now(),
    closed_at     timestamptz,
    check (closed_at is null or closed_at >= opened_at)
);

-- nhiều-nhiều: một tài khoản có thể có chủ + người được uỷ quyền
create table oltp_demo.account_holder (
    account_id    bigint references oltp_demo.account,
    customer_id   bigint references oltp_demo.customer,
    role          text not null check (role in ('owner', 'authorized')),
    primary key (account_id, customer_id)
);
create unique index one_owner_per_account on oltp_demo.account_holder (account_id) where role = 'owner';

create table oltp_demo.transaction (
    transaction_id bigint generated always as identity primary key,
    account_id     bigint not null references oltp_demo.account,
    posted_at      timestamptz not null default now(),
    amount         numeric(18, 2) not null check (amount <> 0),   -- dương = tiền vào, âm = tiền ra
    channel        text not null check (channel in ('branch', 'atm', 'card', 'transfer', 'system')),
    reference      text,
    idempotency_key text unique                                   -- chống ghi trùng khi client gửi lại
);
create index transaction_account_time on oltp_demo.transaction (account_id, posted_at);

select table_name from information_schema.tables where table_schema = 'oltp_demo' order by 1;
