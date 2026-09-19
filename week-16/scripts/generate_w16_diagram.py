"""
Generate the Week 16 Agentic Architecture Diagram.
Illustrates:
1. Multi-Agent Coordination Structure (Coordinator, Investigator, Auditor)
2. Agentic Reasoning & Stopping Condition Loops
3. Context Engineering: Compacted Evidence Dossier & Progressive Skill Disclosure
4. Tool Execution & Failure Isolation Layer
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path


def create_agentic_architecture_diagram():
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    ax.set_facecolor("#0F172A")  # Deep slate dark mode
    fig.patch.set_facecolor("#0F172A")

    # Color Palette
    PRIMARY = "#38BDF8"       # Bright Sky Blue
    SECONDARY = "#818CF8"     # Indigo
    ACCENT = "#34D399"        # Emerald Green
    WARNING = "#FBBF24"       # Amber
    DANGER = "#F87171"        # Coral Red
    CARD_BG = "#1E293B"       # Slate Card
    BORDER = "#334155"        # Slate Border
    TEXT_MAIN = "#F8FAFC"
    TEXT_MUTED = "#94A3B8"

    # Title Header
    ax.text(
        0.5, 0.96,
        "ShopAssist AI: Agentic Multi-Specialist Architecture (Week 16)",
        ha="center", va="center", fontsize=20, fontweight="bold", color=TEXT_MAIN,
        fontfamily="sans-serif"
    )
    ax.text(
        0.5, 0.93,
        "Context Isolation • Compacted External Dossier • Independent Policy Auditor • Progressive Skills",
        ha="center", va="center", fontsize=12, color=PRIMARY,
        fontfamily="sans-serif"
    )

    def draw_card(x, y, w, h, title, subtitle="", color=BORDER, bg=CARD_BG, lw=1.8):
        box = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.025",
            facecolor=bg, edgecolor=color, linewidth=lw
        )
        ax.add_patch(box)
        if title:
            ax.text(
                x + w/2, y + h - 0.035, title,
                ha="center", va="center", fontsize=12, fontweight="bold", color=TEXT_MAIN
            )
        if subtitle:
            ax.text(
                x + w/2, y + h - 0.07, subtitle,
                ha="center", va="center", fontsize=9.5, color=TEXT_MUTED
            )
        return box

    def draw_arrow(x1, y1, x2, y2, label="", color=PRIMARY, style="->", rad=0.0, lw=1.8):
        conn = patches.ConnectionStyle(f"arc3,rad={rad}")
        ax.annotate(
            label, xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle=style, color=color, lw=lw,
                connectionstyle=conn, shrinkA=5, shrinkB=5
            ),
            ha="center", va="center", fontsize=9, color=color, fontweight="semibold"
        )

    # 1. User & Interface Layer
    draw_card(0.04, 0.68, 0.22, 0.20, "Customer / User Client", "FastAPI / Streamlit UI / CLI", color=PRIMARY)
    ax.text(0.15, 0.77, "• Complex Multi-Step Inquiries\n• Damaged / Return Claims\n• Cross-SKU Exchanges\n• Ambiguous Requests", color=TEXT_MAIN, fontsize=9.5, va="top", ha="center")

    # 2. Support Coordinator Agent
    draw_card(0.32, 0.62, 0.36, 0.26, "Customer Support Coordinator", "Dialogue Manager & Resolution Synthesizer", color=PRIMARY, lw=2.2)
    ax.text(0.50, 0.76, "• Dialogue State & Memory Management\n• Ambiguity Detection (Prompt Clarification)\n• Task Directive Delegation to Sub-Agent\n• Synthesizes Final Grounded Response", color=TEXT_MAIN, fontsize=9.5, va="top", ha="center")

    # 3. Evidence Investigator Sub-Agent
    draw_card(0.72, 0.62, 0.24, 0.26, "Evidence Investigator", "Verbose Explorer Sub-Agent", color=SECONDARY, lw=2.0)
    ax.text(0.84, 0.76, "• Context Isolation\n• Autonomous Tool Calling Loop\n• RAG Policy Document Lookup\n• Dynamic Failure Interception", color=TEXT_MAIN, fontsize=9.5, va="top", ha="center")

    # 4. Context Engineering: Compacted Evidence Dossier & Progressive Skills
    draw_card(0.72, 0.34, 0.24, 0.22, "Compacted Evidence Dossier", "Structured External Memory", color=ACCENT, lw=2.0)
    ax.text(0.84, 0.46, "• Context Compaction (-70% Tokens)\n• Order & Carrier Status State\n• Active Verified Inventory\n• Discrepancy & Anomaly Ledger", color=TEXT_MAIN, fontsize=9.2, va="top", ha="center")

    draw_card(0.04, 0.34, 0.22, 0.22, "Progressive Disclosure Skills", "SKILL.md On-Demand Loader", color=ACCENT, lw=2.0)
    ax.text(0.15, 0.46, "• Light Manifest in Initial Prompt\n• Prevents 'Skill Dilution'\n• load_skill('dispute_resolution')\n• load_skill('exchange_fulfillment')", color=TEXT_MAIN, fontsize=9.2, va="top", ha="center")

    # 5. Operational Tools & Knowledge Base
    draw_card(0.32, 0.05, 0.64, 0.24, "Operational Tools & Domain Services (Tool Registry)", "Bounded APIs with Failure Injection Hooks", color=BORDER)
    
    # Sub-tool boxes
    tools = [
        ("order_lookup", "Order DB (Mock)", 0.34, 0.08),
        ("calculate_refund", "Refund Matrix", 0.49, 0.08),
        ("track_shipping", "Carrier API (FedEx/UPS)", 0.65, 0.08),
        ("check_inventory", "Warehouse Stock", 0.81, 0.08)
    ]
    for name, desc, tx, ty in tools:
        t_box = patches.FancyBboxPatch(
            (tx, ty), 0.14, 0.12,
            boxstyle="round,pad=0.01,rounding_size=0.015",
            facecolor="#0B132B", edgecolor=PRIMARY, linewidth=1.2
        )
        ax.add_patch(t_box)
        ax.text(tx + 0.07, ty + 0.08, name, ha="center", va="center", color=PRIMARY, fontsize=9, fontweight="bold")
        ax.text(tx + 0.07, ty + 0.04, desc, ha="center", va="center", color=TEXT_MUTED, fontsize=8)

    # 6. Policy Auditor Agent (Independent Verifier)
    draw_card(0.32, 0.34, 0.36, 0.22, "Policy Auditor Agent (Verifier)", "Independent Verifier (Solves Self-Verification Paradox)", color=WARNING, lw=2.2)
    ax.text(0.50, 0.45, "• Ground-Truth Consistency Audit\n• Enforces Warranty Return Windows\n• Restocking Fee Policy Verification\n• Stock Availability Enforcement", color=TEXT_MAIN, fontsize=9.5, va="top", ha="center")

    # Connections & Flows
    draw_arrow(0.26, 0.78, 0.32, 0.78, "1. User Query", color=PRIMARY)
    draw_arrow(0.68, 0.80, 0.72, 0.80, "2. Delegate Task", color=SECONDARY)
    draw_arrow(0.84, 0.62, 0.84, 0.56, "3. Context Compaction", color=ACCENT)
    draw_arrow(0.84, 0.62, 0.84, 0.29, "Tool Execution", color=BORDER, rad=0.2)
    draw_arrow(0.26, 0.45, 0.72, 0.45, "On-Demand Skill Disclosure", color=ACCENT, style="<->")
    draw_arrow(0.72, 0.42, 0.68, 0.42, "4. Structured Notes", color=ACCENT)
    draw_arrow(0.50, 0.62, 0.50, 0.56, "5. Candidate Resolution", color=WARNING)
    draw_arrow(0.42, 0.56, 0.42, 0.62, "6. Audit Result / Repair", color=WARNING, rad=-0.2)
    draw_arrow(0.32, 0.72, 0.26, 0.72, "7. Verified Answer", color=ACCENT)

    # Stopping condition badge
    stop_box = patches.FancyBboxPatch(
        (0.04, 0.12), 0.22, 0.14,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="#1A1F2C", edgecolor=DANGER, linewidth=1.5
    )
    ax.add_patch(stop_box)
    ax.text(0.15, 0.21, "Stopping Conditions", ha="center", va="center", color=DANGER, fontsize=10.5, fontweight="bold")
    ax.text(0.15, 0.16, "• Status == RESOLVED\n• Max Iterations == 5 Guard\n• Clarification Prompted", ha="center", va="center", color=TEXT_MAIN, fontsize=8.5)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    out_path = Path(__file__).resolve().parent.parent / "outputs" / "agentic_architecture.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"[+] Successfully generated architecture diagram: {out_path}")


if __name__ == "__main__":
    create_agentic_architecture_diagram()
