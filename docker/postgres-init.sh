#!/bin/bash
# Runs once on first start of the postgres container.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<SQL
CREATE DATABASE airflow;
CREATE ROLE analyst_ro LOGIN PASSWORD '${ANALYST_RO_PASSWORD}';
SQL
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname bank <<SQL
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE bank TO analyst_ro;
ALTER ROLE analyst_ro SET default_transaction_read_only = on;
ALTER ROLE analyst_ro SET statement_timeout = '10s';
SQL
