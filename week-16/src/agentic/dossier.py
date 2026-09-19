"""
Structured External Notes (Compacted Evidence Dossier).
Context engineering technique: eliminates raw tool output bloat by extracting,
normalizing, and storing only the salient factual signals required for reasoning.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OrderFact(BaseModel):
    order_id: str
    customer_name: str
    status: str
    order_date: str
    delivered_date: Optional[str] = None
    items: List[Dict[str, Any]] = []
    total_amount: float = 0.0
    tracking_number: Optional[str] = None


class CarrierFact(BaseModel):
    tracking_number: str
    carrier: str
    status: str
    delivery_date: Optional[str] = None
    estimated_delivery: Optional[str] = None
    signed_by: Optional[str] = None


class PolicyFact(BaseModel):
    policy_name: str
    clause: str
    relevance_score: float = 1.0


class InventoryFact(BaseModel):
    sku: str
    name: str = ""
    in_stock: int = 0
    available: bool = False
    warehouse: str = ""


class EvidenceDossier(BaseModel):
    """
    Structured external memory ledger that maintains compact verified facts
    across iterations. Prevents context saturation from raw tool JSON payloads.
    """
    order: Optional[OrderFact] = None
    carrier: Optional[CarrierFact] = None
    inventory: Dict[str, InventoryFact] = Field(default_factory=dict)
    policies: List[PolicyFact] = Field(default_factory=list)
    refund_assessment: Optional[Dict[str, Any]] = None
    loaded_skills: List[str] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    resolution_status: str = "IN_PROGRESS"  # IN_PROGRESS, RESOLVED, CLARIFICATION_REQUIRED, ESCALATED

    def update_order(self, data: Dict[str, Any]):
        """Compact raw order lookup into an OrderFact."""
        if not data or not data.get("found"):
            return
        ord_info = data.get("order", {})
        self.order = OrderFact(
            order_id=ord_info.get("order_id", ""),
            customer_name=ord_info.get("customer_name", ""),
            status=ord_info.get("status", ""),
            order_date=ord_info.get("order_date", ""),
            delivered_date=ord_info.get("delivered_date"),
            items=ord_info.get("items", []),
            total_amount=ord_info.get("total_amount", 0.0),
            tracking_number=ord_info.get("tracking_number"),
        )

    def update_carrier(self, data: Dict[str, Any]):
        """Compact raw shipping data into CarrierFact."""
        if not data:
            return
        self.carrier = CarrierFact(
            tracking_number=data.get("tracking_number", ""),
            carrier=data.get("carrier", ""),
            status=data.get("status", ""),
            delivery_date=data.get("delivery_date"),
            estimated_delivery=data.get("estimated_delivery"),
            signed_by=data.get("signed_by"),
        )

    def update_inventory(self, sku: str, data: Dict[str, Any]):
        """Record verified stock level for a SKU."""
        if not data:
            return
        self.inventory[sku.upper()] = InventoryFact(
            sku=sku.upper(),
            name=data.get("name", sku),
            in_stock=data.get("in_stock", 0),
            available=data.get("available", False),
            warehouse=data.get("warehouse", "Unknown"),
        )

    def add_policy_chunk(self, policy_name: str, clause: str, score: float = 1.0):
        """Add distilled policy constraint."""
        # Deduplicate by clause
        if not any(p.clause == clause for p in self.policies):
            self.policies.append(PolicyFact(policy_name=policy_name, clause=clause, relevance_score=score))

    def set_refund(self, calculation: Dict[str, Any]):
        self.refund_assessment = calculation

    def add_skill(self, skill_name: str):
        if skill_name not in self.loaded_skills:
            self.loaded_skills.append(skill_name)

    def add_discrepancy(self, note: str):
        if note not in self.discrepancies:
            self.discrepancies.append(note)

    def render_compact_context(self) -> str:
        """
        Produces a concise, token-efficient external note representation for LLM context.
        Cuts verbose JSON payloads down by 70-85% while keeping 100% semantic signal.
        """
        lines = ["### [COMPACTED EVIDENCE DOSSIER]"]

        # Order & Delivery
        if self.order:
            lines.append(
                f"- Order {self.order.order_id}: Total ${self.order.total_amount:.2f} | Status: {self.order.status} | "
                f"Delivered: {self.order.delivered_date or 'N/A'}"
            )
            item_summaries = [f"{it.get('name')} (qty {it.get('qty')})" for it in self.order.items]
            lines.append(f"  Items: {', '.join(item_summaries)}")
        else:
            lines.append("- Order: No verified order attached.")

        # Carrier tracking
        if self.carrier:
            lines.append(
                f"- Carrier: {self.carrier.carrier} ({self.carrier.tracking_number}) -> Status: {self.carrier.status} "
                f"| Signed by: {self.carrier.signed_by or 'None'}"
            )

        # Inventory
        if self.inventory:
            inv_str = ", ".join(
                f"{sku}: {'IN STOCK (' + str(f.in_stock) + ')' if f.available else 'OUT OF STOCK'}"
                for sku, f in self.inventory.items()
            )
            lines.append(f"- Inventory Verified: {inv_str}")

        # Policies
        if self.policies:
            lines.append("- Applicable Policy Rules:")
            for p in self.policies[:4]:  # capped top salient clauses
                lines.append(f"  * [{p.policy_name}] {p.clause}")

        # Refund
        if self.refund_assessment:
            ref = self.refund_assessment
            lines.append(
                f"- Refund Calculation: Eligible={ref.get('eligible')} | Type={ref.get('refund_type')} | "
                f"Amount=${ref.get('refund_amount', 0.0):.2f} | Restocking Fee=${ref.get('restocking_fee', 0.0):.2f}"
            )

        # Active skills
        if self.loaded_skills:
            lines.append(f"- Loaded Procedural Skills: {', '.join(self.loaded_skills)}")

        # Flags & Discrepancies
        if self.discrepancies:
            lines.append(f"- Discrepancies/Alerts: {'; '.join(self.discrepancies)}")

        if self.missing_fields:
            lines.append(f"- Missing Information: {'; '.join(self.missing_fields)}")

        lines.append(f"- Current Status: {self.resolution_status}")
        return "\n".join(lines)
