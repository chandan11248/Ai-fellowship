"""
Script to generate the architecture diagram graphic for Week 15 deliverables.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from src.config import settings


def generate_architecture_diagram(output_path: Path):
    fig, ax = plt.subplots(figsize=(14, 9), dpi=200)
    fig.patch.set_facecolor("#0F172A")
    ax.set_facecolor("#0F172A")

    # Title
    plt.title("ShopAssist AI Assistant - System Architecture (Applied AI & Systems Engineering)",
              fontsize=16, fontweight="bold", color="#F8FAFC", pad=20)

    # Box styles
    def draw_box(x, y, w, h, label, sublabel="", color="#1E293B", border="#38BDF8", text_color="#F8FAFC"):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.04",
                                      linewidth=1.8, edgecolor=border, facecolor=color)
        ax.add_patch(rect)
        if sublabel:
            ax.text(x + w/2, y + h/2 + 0.02, label, ha="center", va="center", color=text_color,
                    fontsize=10, fontweight="bold")
            ax.text(x + w/2, y + h/2 - 0.025, sublabel, ha="center", va="center", color="#94A3B8",
                    fontsize=8)
        else:
            ax.text(x + w/2, y + h/2, label, ha="center", va="center", color=text_color,
                    fontsize=10, fontweight="bold")

    # Connectors
    def draw_arrow(x1, y1, x2, y2, label="", color="#38BDF8"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, mutation_scale=14))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2 + 0.015, label, color="#E2E8F0", fontsize=8, ha="center",
                    backgroundcolor="#0F172A")

    # 1. UI Layer
    draw_box(0.05, 0.72, 0.22, 0.16, "Web User Interface", "Streamlit / React / Client",
             color="#1E293B", border="#818CF8")

    # 2. API Gateway & Middleware
    draw_box(0.35, 0.72, 0.28, 0.16, "FastAPI Backend Gateway", "Async • Rate Limiting • Middleware",
             color="#1E293B", border="#38BDF8")
    draw_arrow(0.27, 0.80, 0.35, 0.80, "HTTP / SSE")

    # 3. Response Cache
    draw_box(0.70, 0.72, 0.25, 0.16, "Prompt & Response Cache", "In-Memory LRU / Redis Cache",
             color="#1E293B", border="#34D399")
    draw_arrow(0.63, 0.80, 0.70, 0.80, "Cache Check")

    # 4. Assistant Orchestrator Agent
    draw_box(0.35, 0.44, 0.28, 0.16, "AI Assistant Agent", "Reasoning Loop • Tool Dispatcher",
             color="#1E293B", border="#F59E0B")
    draw_arrow(0.49, 0.72, 0.49, 0.60, "Request Context")

    # 5. RAG Pipeline
    draw_box(0.05, 0.44, 0.22, 0.16, "RAG Pipeline Engine", "Ingestion • Chunking • Cosine Sim",
             color="#1E293B", border="#06B6D4")
    draw_arrow(0.27, 0.52, 0.35, 0.52, "Grounded Chunks")

    # 6. Vector Database
    draw_box(0.05, 0.16, 0.22, 0.16, "Vector Store", "ChromaDB / Persistent Index",
             color="#1E293B", border="#06B6D4")
    draw_arrow(0.16, 0.32, 0.16, 0.44, "Top-K Search")

    # 7. Function / Tool Calling Engine
    draw_box(0.70, 0.44, 0.25, 0.16, "Tool Calling Engine", "Order Lookup • Refunds • Tracking",
             color="#1E293B", border="#EC4899")
    draw_arrow(0.63, 0.52, 0.70, 0.52, "Tool Invocation")

    # 8. Reliability & Fallback Manager
    draw_box(0.35, 0.16, 0.28, 0.16, "Reliability & Fallback", "Circuit Breaker • Exponential Retries",
             color="#1E293B", border="#F43F5E")
    draw_arrow(0.49, 0.44, 0.49, 0.32, "Dispatch Call")

    # 9. Multi-tier LLM & ONNX Providers
    draw_box(0.70, 0.16, 0.25, 0.16, "Model Providers", "Cloud LLMs • vLLM • Local ONNX",
             color="#1E293B", border="#A855F7")
    draw_arrow(0.63, 0.24, 0.70, 0.24, "Inference Tier")

    ax.set_xlim(0, 1.0)
    ax.set_ylim(0.05, 0.98)
    ax.axis("off")

    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=200)
    plt.close()
    print(f"[Architecture Diagram] Generated and saved to: {output_path}")


if __name__ == "__main__":
    out = settings.BASE_DIR / "outputs" / "architecture_diagram.png"
    generate_architecture_diagram(out)
