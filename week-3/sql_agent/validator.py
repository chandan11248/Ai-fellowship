from __future__ import annotations

import re


class UnsafeSQLError(ValueError):
    """Raised when generated SQL is not a safe read-only SELECT statement."""


BLOCKED_KEYWORDS = {
    "alter",
    "call",
    "copy",
    "create",
    "delete",
    "drop",
    "execute",
    "grant",
    "insert",
    "merge",
    "revoke",
    "truncate",
    "update",
}


def _strip_string_literals(sql: str) -> str:
    return re.sub(r"'(?:''|[^'])*'", "''", sql)


def validate_select_only(sql: str) -> str:
    statement = sql.strip()
    if not re.match(r"(?is)^select\b", statement):
        raise UnsafeSQLError("Only SELECT statements are allowed.")

    without_final_semicolon = statement[:-1] if statement.endswith(";") else statement
    if ";" in without_final_semicolon:
        raise UnsafeSQLError("Multiple SQL statements are not allowed.")

    token_source = _strip_string_literals(without_final_semicolon.lower())
    tokens = set(re.findall(r"\b[a-z_]+\b", token_source))
    blocked = sorted(tokens & BLOCKED_KEYWORDS)
    if blocked:
        raise UnsafeSQLError(f"Blocked SQL keyword(s): {', '.join(blocked)}")

    return statement
