"""
Tests for Tool Registry and Function Calling.
"""

import pytest
from src.assistant.tool_registry import (
    ToolRegistry,
    order_lookup,
    calculate_refund,
    track_shipping_package,
    check_item_inventory,
    registry
)


def test_custom_tool_registration():
    custom_reg = ToolRegistry()

    @custom_reg.register(name="add_numbers", description="Add two numbers together.")
    def add(a: int, b: int) -> int:
        return a + b

    schemas = custom_reg.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "add_numbers"
    assert "a" in schemas[0]["function"]["parameters"]["properties"]

    res = custom_reg.execute("add_numbers", {"a": 10, "b": 25})
    assert res["success"] is True
    assert res["result"] == 35


def test_order_lookup_found():
    res = order_lookup("ORD-1001")
    assert res["found"] is True
    assert res["order"]["customer_name"] == "Alice Johnson"
    assert res["order"]["total_amount"] == 149.99


def test_order_lookup_not_found():
    res = order_lookup("ORD-999999")
    assert res["found"] is False


def test_calculate_refund_unopened():
    res = calculate_refund(
        order_id="ORD-1001",
        return_reason="Changed mind",
        days_since_delivery=10,
        item_condition="unopened"
    )
    assert res["eligible"] is True
    assert res["refund_type"] == "FULL_REFUND"
    assert res["refund_amount"] == 149.99
    assert res["restocking_fee"] == 0.0


def test_calculate_refund_opened_restocking():
    res = calculate_refund(
        order_id="ORD-1001",
        return_reason="Did not like color",
        days_since_delivery=15,
        item_condition="opened"
    )
    assert res["eligible"] is True
    assert res["refund_type"] == "PARTIAL_REFUND"
    assert res["restocking_fee"] > 0.0


def test_calculate_refund_defective():
    res = calculate_refund(
        order_id="ORD-1001",
        return_reason="Item arrived broken and defective",
        days_since_delivery=60,
        item_condition="opened"
    )
    assert res["eligible"] is True
    assert res["refund_type"] == "FULL_REFUND"


def test_track_shipping():
    res = track_shipping_package("TRK-987654321")
    assert res["status"] == "DELIVERED"
    assert res["carrier"] == "FedEx Express"


def test_check_inventory():
    res = check_item_inventory("SKU-HEADPHONES-01")
    assert res["available"] is True
    assert res["in_stock"] > 0
