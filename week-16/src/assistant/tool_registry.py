"""
Tool registry and function calling infrastructure.
Enables tool definition via decorators, automatic JSON schema generation,
parameter validation, and safe sandboxed execution.
"""

import inspect
import json
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime, timezone


class ToolRegistry:
    """Registry that holds tool definitions and handles dispatching."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._injected_failures: Dict[str, Dict[str, Any]] = {}

    def inject_failure(self, tool_name: str, failure_type: str = "unavailable", details: Optional[Dict[str, Any]] = None):
        """Intentionally inject failure into a tool for robustness testing."""
        self._injected_failures[tool_name] = {
            "type": failure_type,
            "details": details or {}
        }

    def clear_failures(self):
        """Remove all active failure injections."""
        self._injected_failures.clear()

    def register(self, name: Optional[str] = None, description: Optional[str] = None):
        """Decorator to register a Python function as an executable tool."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "No description provided.").strip()

            # Inspect parameters to build OpenAI-compatible tool JSON schema
            sig = inspect.signature(func)
            properties: Dict[str, Any] = {}
            required_params: List[str] = []

            type_mapping = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
                dict: "object",
                list: "array",
            }

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                param_type = type_mapping.get(param.annotation, "string")
                properties[param_name] = {
                    "type": param_type,
                    "description": f"Parameter {param_name}"
                }
                if param.default is inspect.Parameter.empty:
                    required_params.append(param_name)

            schema = {
                "name": tool_name,
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params,
                }
            }

            self._tools[tool_name] = func
            self._schemas[tool_name] = schema
            return func
        return decorator

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return list of all registered tool schemas in OpenAI function format."""
        return [
            {"type": "function", "function": schema}
            for schema in self._schemas.values()
        ]

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with provided arguments safely, observing failure injections."""
        # Check for injected failure simulation
        if tool_name in self._injected_failures:
            failure_info = self._injected_failures[tool_name]
            f_type = failure_info.get("type", "unavailable")
            if f_type == "unavailable":
                return {
                    "success": False,
                    "tool_name": tool_name,
                    "error": f"HTTP 503 Service Unavailable: Remote endpoint for '{tool_name}' is currently unreachable.",
                    "status_code": 503
                }
            elif f_type == "malformed":
                return {
                    "success": True,
                    "tool_name": tool_name,
                    "result": "CORRUPTED_RAW_STREAM: \x00\x01\xfe\xff [UNPARSABLE BYTES] key error at offset 0",
                    "status_code": 200
                }
            elif f_type == "timeout":
                return {
                    "success": False,
                    "tool_name": tool_name,
                    "error": f"TimeoutError: Request to '{tool_name}' timed out after 30000ms without response.",
                    "status_code": 504
                }

        if tool_name not in self._tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
            }

        func = self._tools[tool_name]
        try:
            result = func(**arguments)
            return {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except TypeError as exc:
            return {
                "success": False,
                "tool_name": tool_name,
                "error": f"Invalid arguments for {tool_name}: {str(exc)}"
            }
        except Exception as exc:
            return {
                "success": False,
                "tool_name": tool_name,
                "error": f"Tool execution failed: {str(exc)}"
            }


# Default global tool registry
registry = ToolRegistry()


# =========================================================================
# Built-in Customer Support & Enterprise Tools
# =========================================================================

# Mock In-Memory Databases for deterministic execution
MOCK_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_name": "Alice Johnson",
        "email": "alice@example.com",
        "status": "DELIVERED",
        "order_date": "2026-08-20",
        "delivered_date": "2026-08-24",
        "items": [
            {"sku": "SKU-HEADPHONES-01", "name": "Wireless Noise Cancelling Headphones", "qty": 1, "price": 149.99}
        ],
        "total_amount": 149.99,
        "shipping_carrier": "FedEx",
        "tracking_number": "TRK-987654321"
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_name": "Bob Smith",
        "email": "bob@example.com",
        "status": "IN_TRANSIT",
        "order_date": "2026-08-28",
        "delivered_date": None,
        "items": [
            {"sku": "SKU-KEYBOARD-PRO", "name": "Mechanical Gaming Keyboard RGB", "qty": 1, "price": 89.50},
            {"sku": "SKU-MOUSE-PAD", "name": "Desk Mat XL", "qty": 1, "price": 24.00}
        ],
        "total_amount": 113.50,
        "shipping_carrier": "UPS",
        "tracking_number": "TRK-123456789"
    }
}

MOCK_INVENTORY = {
    "SKU-HEADPHONES-01": {"name": "Wireless Noise Cancelling Headphones", "in_stock": 42, "warehouse": "US-East-1"},
    "SKU-KEYBOARD-PRO": {"name": "Mechanical Gaming Keyboard RGB", "in_stock": 18, "warehouse": "US-West-2"},
    "SKU-MOUSE-PAD": {"name": "Desk Mat XL", "in_stock": 120, "warehouse": "US-Central-1"},
}


@registry.register(
    name="order_lookup",
    description="Lookup details of a customer order by its unique Order ID (e.g. ORD-1001)."
)
def order_lookup(order_id: str) -> Dict[str, Any]:
    """Retrieve full order details including line items, status, and shipping info."""
    clean_id = order_id.strip().upper()
    order = MOCK_ORDERS.get(clean_id)
    if not order:
        return {
            "found": False,
            "message": f"Order with ID '{clean_id}' was not found in the database."
        }
    return {"found": True, "order": order}


@registry.register(
    name="calculate_refund",
    description="Calculate refund eligibility, return fees, and total refundable amount for an order."
)
def calculate_refund(
    order_id: str,
    return_reason: str,
    days_since_delivery: int,
    item_condition: str = "unopened"
) -> Dict[str, Any]:
    """
    Evaluates store refund policy:
    - Within 30 days: 100% full refund if unopened, 85% if opened in good condition.
    - 31-45 days: Store credit only, subject to 15% restocking fee.
    - > 45 days: Ineligible for standard return.
    - Defective items: 100% refund or free replacement within 90 days.
    """
    clean_id = order_id.strip().upper()
    order = MOCK_ORDERS.get(clean_id)
    subtotal = order["total_amount"] if order else 100.0

    reason_lower = return_reason.lower()
    is_defective = "defective" in reason_lower or "broken" in reason_lower or "damaged" in reason_lower

    if is_defective:
        if days_since_delivery <= 90:
            return {
                "eligible": True,
                "refund_type": "FULL_REFUND",
                "refund_amount": subtotal,
                "restocking_fee": 0.0,
                "return_shipping_covered": True,
                "policy_note": "Defective item warranty covers 100% refund or free replacement within 90 days."
            }
        else:
            return {
                "eligible": False,
                "refund_type": "EXPIRED_WARRANTY",
                "refund_amount": 0.0,
                "policy_note": "Defective warranty claims must be submitted within 90 days of delivery."
            }

    if days_since_delivery <= 30:
        if item_condition.lower() == "unopened":
            return {
                "eligible": True,
                "refund_type": "FULL_REFUND",
                "refund_amount": subtotal,
                "restocking_fee": 0.0,
                "return_shipping_covered": True,
                "policy_note": "Unopened items within 30 days are eligible for full refund."
            }
        else:
            restocking = round(subtotal * 0.15, 2)
            return {
                "eligible": True,
                "refund_type": "PARTIAL_REFUND",
                "refund_amount": round(subtotal - restocking, 2),
                "restocking_fee": restocking,
                "return_shipping_covered": False,
                "policy_note": "Opened items within 30 days are subject to a 15% inspection & restocking fee."
            }
    elif days_since_delivery <= 45:
        restocking = round(subtotal * 0.15, 2)
        return {
            "eligible": True,
            "refund_type": "STORE_CREDIT",
            "refund_amount": round(subtotal - restocking, 2),
            "restocking_fee": restocking,
            "policy_note": "Returns between 31 and 45 days receive Store Credit minus 15% restocking fee."
        }
    else:
        return {
            "eligible": False,
            "refund_type": "NON_REFUNDABLE",
            "refund_amount": 0.0,
            "policy_note": "Items returned beyond 45 days are not eligible for refunds or store credits."
        }


@registry.register(
    name="track_shipping_package",
    description="Track real-time carrier delivery status and milestones by tracking number."
)
def track_shipping_package(tracking_number: str) -> Dict[str, Any]:
    """Retrieve tracking milestones and ETA."""
    clean_trk = tracking_number.strip().upper()
    if clean_trk.startswith("TRK-987"):
        return {
            "tracking_number": clean_trk,
            "carrier": "FedEx Express",
            "status": "DELIVERED",
            "delivery_date": "2026-08-24 14:22:00",
            "signed_by": "A. Johnson (Front Porch)",
            "origin": "Memphis, TN",
            "destination": "San Francisco, CA"
        }
    elif clean_trk.startswith("TRK-123"):
        return {
            "tracking_number": clean_trk,
            "carrier": "UPS Ground",
            "status": "OUT_FOR_DELIVERY",
            "estimated_delivery": "2026-08-31 by 19:00",
            "current_location": "Oakland Sorting Hub, CA",
            "origin": "Louisville, KY",
            "destination": "San Francisco, CA"
        }
    else:
        return {
            "tracking_number": clean_trk,
            "carrier": "Standard Carrier",
            "status": "IN_TRANSIT",
            "estimated_delivery": "2-3 business days",
            "current_location": "Regional Distribution Center"
        }


@registry.register(
    name="check_item_inventory",
    description="Check stock availability and warehouse fulfillment location by SKU (e.g. SKU-HEADPHONES-01)."
)
def check_item_inventory(sku: str) -> Dict[str, Any]:
    """Retrieve SKU inventory levels and warehouse status."""
    clean_sku = sku.strip().upper()
    item = MOCK_INVENTORY.get(clean_sku)
    if not item:
        return {"sku": clean_sku, "in_stock": 0, "available": False, "message": "SKU not found in catalog."}
    return {"sku": clean_sku, "in_stock": item["in_stock"], "available": item["in_stock"] > 0, "warehouse": item["warehouse"]}


@registry.register(
    name="load_skill",
    description="Dynamically load detailed procedural instructions for a specialized workflow (e.g. 'dispute_resolution', 'exchange_fulfillment')."
)
def load_skill(skill_name: str) -> Dict[str, Any]:
    """Progressive disclosure tool: loads full procedural instructions on demand."""
    from src.agentic.skills_manager import skills_manager
    return skills_manager.load_skill(skill_name)


@registry.register(
    name="search_policies",
    description="Search store policy documents for return eligibility, warranty rules, shipping, and exceptions."
)
def search_policies(query: str) -> Dict[str, Any]:
    """RAG semantic lookup for store policy constraints."""
    from src.rag.pipeline import rag_pipeline
    docs = rag_pipeline.retrieve(query, top_k=3)
    results = [
        {"content": d.content, "metadata": d.metadata, "similarity": round(d.similarity, 4)}
        for d in docs
    ]
    return {"query": query, "count": len(results), "documents": results}

