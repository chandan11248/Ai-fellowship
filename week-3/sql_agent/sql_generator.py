from __future__ import annotations

import re
from typing import Any

from .benchmark import BenchmarkSpec, find_spec, normalize_question


RETRY_DEMO_BAD_SQL = "SELECT product_name FROM products LIMIT 3;"


def decompose_question(question: str) -> dict[str, Any]:
    normalized = normalize_question(question)
    if normalized == "retry demo: product names":
        return {
            "intent": "Demonstrate retry repair for a common column naming mistake",
            "tables": ["products"],
            "columns": ['"productName"'],
            "filters": "None",
            "joins": "None",
        }

    shipped_country = _parse_shipped_orders_by_country(question)
    if shipped_country:
        return {
            "intent": "Count shipped orders for customers in a country",
            "tables": ["orders", "customers"],
            "columns": ["COUNT(*)", 'orders."status"', 'customers."country"'],
            "filters": f"orders.status = 'Shipped' AND customers.country = '{shipped_country}'",
            "joins": "customers.customerNumber = orders.customerNumber",
        }

    spec = find_spec(question)
    return spec_to_decomposition(spec)


def spec_to_decomposition(spec: BenchmarkSpec) -> dict[str, Any]:
    return {
        "intent": spec.intent,
        "tables": list(spec.tables),
        "columns": list(spec.columns),
        "filters": spec.filters,
        "joins": spec.joins,
    }


def generate_sql(question: str) -> str:
    normalized = normalize_question(question)
    if normalized == "retry demo: product names":
        return RETRY_DEMO_BAD_SQL

    shipped_country = _parse_shipped_orders_by_country(question)
    if shipped_country:
        country = shipped_country.replace("'", "''")
        return (
            "SELECT COUNT(*) AS shipped_order_count\n"
            "FROM orders o\n"
            'JOIN customers c ON c."customerNumber" = o."customerNumber"\n'
            f'WHERE o."status" = \'Shipped\' AND c."country" = \'{country}\';'
        )

    return find_spec(question).sql


def repair_sql(sql: str, error_message: str) -> str:
    repaired = sql
    replacements = {
        "product_name": '"productName"',
        '"product_name"': '"productName"',
        '"product_code"': '"productCode"',
        '"customer_number"': '"customerNumber"',
        '"customer_name"': '"customerName"',
        '"order_number"': '"orderNumber"',
        '"product_line"': '"productLine"',
    }
    lowered_error = error_message.lower()
    for wrong, correct in replacements.items():
        if wrong.lower().strip('"') in lowered_error or wrong in repaired:
            repaired = repaired.replace(wrong, correct)
    return repaired


def summarize_result(question: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "The query returned no rows."

    normalized = normalize_question(question)
    first_row = rows[0]
    if normalized.startswith("how many shipped orders"):
        value = next(iter(first_row.values()))
        country_match = re.search(r"\bfrom\s+([a-zA-Z ]+?)\s+customers\b", question, re.IGNORECASE)
        country = country_match.group(1).strip() if country_match else "the requested"
        return f"There are {value} shipped orders from customers in {country}."

    if len(rows) == 1 and len(first_row) == 1:
        label, value = next(iter(first_row.items()))
        readable_label = label.replace("_", " ")
        return f"The {readable_label} is {value}."

    return f"The query returned {len(rows)} rows."


def _parse_shipped_orders_by_country(question: str) -> str | None:
    match = re.search(
        r"how many shipped orders are from ([a-zA-Z ]+?) customers",
        question,
        re.IGNORECASE,
    )
    if not match:
        return None
    country = match.group(1).strip()
    return country.upper() if country.lower() == "usa" else country.title()
