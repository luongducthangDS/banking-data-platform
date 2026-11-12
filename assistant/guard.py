"""Static SQL guard: the LLM's SQL must be one read-only SELECT over allow-listed tables.

This is the first of three layers; the database role (analyst_ro: SELECT on core/marts only,
read-only transactions, statement timeout) is the second, EXPLAIN cost limit the third.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp

ALLOWED_SCHEMAS = {"core", "marts"}
MAX_ROWS = 1000
BLOCKED_FUNCS = ("pg_", "dblink", "lo_", "set_config", "current_setting", "query_to_xml", "copy")
WRITE_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter,
               exp.Command, exp.Grant, exp.Copy, exp.TruncateTable, exp.Set)


class Blocked(Exception):
    pass


def check(sql: str) -> str:
    """Return the SQL to run (with a LIMIT), or raise Blocked with the reason."""
    try:
        stmts = [s for s in sqlglot.parse(sql, dialect="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise Blocked(f"not valid PostgreSQL: {str(e).splitlines()[0]}")
    if len(stmts) != 1:
        raise Blocked("exactly one statement is allowed")
    tree = stmts[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise Blocked(f"only SELECT is allowed, got {tree.key.upper()}")
    for node in tree.walk():
        if isinstance(node, WRITE_NODES):
            raise Blocked(f"{node.key.upper()} is not allowed")
        if isinstance(node, exp.Select) and node.args.get("locks"):
            raise Blocked("row locks (FOR UPDATE/SHARE) are not allowed")
        if isinstance(node, (exp.Anonymous, exp.Func)):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name.startswith(BLOCKED_FUNCS):
                raise Blocked(f"function {name} is not allowed")

    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        schema, name = t.db.lower(), t.name.lower()
        if not schema and name in ctes:
            continue
        if schema not in ALLOWED_SCHEMAS:
            raise Blocked(f"table {t.sql()} is outside the allowed schemas {sorted(ALLOWED_SCHEMAS)}")

    limit = tree.args.get("limit")
    current = None
    if limit is not None:
        try:
            current = int(limit.expression.name)
        except (AttributeError, ValueError):
            raise Blocked("LIMIT must be a number")
    if current is None or current > MAX_ROWS:
        tree = tree.limit(MAX_ROWS, copy=False) if isinstance(tree, exp.Select) else \
            exp.select("*").from_(tree.subquery("q")).limit(MAX_ROWS)
    return tree.sql(dialect="postgres")
