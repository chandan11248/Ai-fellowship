"""
Streamlit user interface for the ShopAssist customer support & document assistant.
Connects to the FastAPI backend with in-process fallback, displaying
chat history, tool calls, document upload, RAG context, and ONNX classification.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import json
import time
import tempfile
import streamlit as st
import requests

from src.config import settings
from src.rag.pipeline import RAGPipeline
from src.rag.ingestion import DocumentLoader

st.set_page_config(
    page_title="ShopAssist AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimal CSS styling
st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        font-size: 0.75rem;
        border-radius: 4px;
        background-color: #f1f5f9;
        color: #334155;
        margin-right: 0.4rem;
    }
    .doc-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        margin: 0.2rem 0.2rem 0.2rem 0;
        border-radius: 12px;
        background-color: #e2e8f0;
        color: #1e293b;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    try:
        r = requests.get(f"http://localhost:{settings.PORT}/health", timeout=1.0)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_api_metrics():
    try:
        r = requests.get(f"http://localhost:{settings.PORT}/metrics", timeout=1.0)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# Global RAG instance helper
@st.cache_resource
def get_shared_rag():
    return RAGPipeline()


rag_instance = get_shared_rag()

# Sidebar controls
with st.sidebar:
    st.subheader("Document Upload & RAG")
    uploaded_file = st.file_uploader(
        "Upload a document (PDF, TXT, MD, CSV, JSON)",
        type=["pdf", "txt", "md", "csv", "json"],
        help="Upload any file to index it into the vector database for Q&A."
    )

    if uploaded_file is not None:
        if st.button("Index Uploaded Document", use_container_width=True):
            with st.spinner("Parsing, chunking, and embedding document..."):
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = Path(tmp.name)

                try:
                    docs = DocumentLoader.load_file(tmp_path)
                    total_chunks = 0
                    for d in docs:
                        d.metadata["source"] = uploaded_file.name
                        chunks = rag_instance.chunker.chunk_document(d)
                        added = rag_instance.store.add_chunks(chunks)
                        total_chunks += added

                        # Also sync with backend API if alive
                        try:
                            requests.post(
                                f"http://localhost:{settings.PORT}/v1/rag/ingest",
                                json={
                                    "doc_id": uploaded_file.name,
                                    "content": d.content,
                                    "metadata": {"source": uploaded_file.name}
                                },
                                timeout=5.0
                            )
                        except Exception:
                            pass

                    st.success(f"Indexed '{uploaded_file.name}' into {total_chunks} vector chunks!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to index document: {e}")
                finally:
                    if tmp_path.exists():
                        tmp_path.unlink()

    # Active Documents in Vector Store
    docs_summary = rag_instance.get_documents_summary()
    st.markdown(f"**Indexed Documents ({rag_instance.store.count()} chunks total):**")
    if docs_summary:
        for item in docs_summary:
            st.markdown(f"<span class='doc-pill'>📄 {item['document']} ({item['chunks']} chunks)</span>", unsafe_allow_html=True)
    else:
        st.caption("No documents in database. Upload a file above!")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Reset / Clear DB", help="Clear all documents from vector store to start clean"):
            rag_instance.clear()
            try:
                requests.post(f"http://localhost:{settings.PORT}/v1/rag/clear", timeout=3.0)
            except Exception:
                pass
            st.warning("Vector database cleared!")
            st.rerun()

    with col_btn2:
        if st.button("Load Defaults", help="Re-index standard customer support policies"):
            if settings.DOCS_DIR.exists():
                count = rag_instance.ingest_directory(settings.DOCS_DIR)
                st.success(f"Loaded {count} default chunks!")
                st.rerun()

    st.divider()
    st.subheader("Settings")

    health_data = check_api_health()
    if health_data:
        st.success(f"Backend API connected ({health_data.get('indexed_chunks', 0)} chunks in API)")
    else:
        st.info("Backend API offline (using direct in-process mode)")

    st.markdown("**Generation parameters**")
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
    top_p = st.slider("Top-p", min_value=0.1, max_value=1.0, value=0.95, step=0.05)
    max_tokens = st.slider("Max tokens", min_value=128, max_value=2048, value=1024, step=64)

    st.markdown("**Options**")
    agentic_mode = st.toggle("Agentic Multi-Specialist Mode (Week 16)", value=True, help="Enables Coordinator -> Investigator -> Compact Dossier -> Policy Auditor loop")
    use_rag = st.toggle("Enable RAG search", value=True)
    use_tools = st.toggle("Enable tool execution", value=True)
    enforce_json = st.toggle("Enforce JSON output", value=False)

    st.divider()
    metrics = get_api_metrics()
    if metrics:
        st.caption(f"Uptime: {metrics['uptime_seconds']}s | Total requests: {metrics['total_requests']}")
        st.caption(f"Cache hit ratio: {metrics['cache_hit_ratio_pct']}%")
        st.caption(f"Circuit breaker: {metrics['circuit_breaker_state']}")

# Main Header
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown('<div class="main-title">ShopAssist AI & Document Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Week 15 & 16 (Multi-Agent Specialist Architecture, Dynamic Loop, Context Compaction, RAG & ONNX)</div>', unsafe_allow_html=True)

with col2:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# Initial conversation state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I am ShopAssist AI (Week 16 Multi-Specialist Edition). You can ask complex warranty questions, request cross-SKU exchanges, track packages, or upload custom documents. How may I assist you?"}
    ]

tab_chat, tab_kb, tab_onnx = st.tabs(["Chat & Document Q&A", "Knowledge Base Explorer", "Intent Classifier (ONNX)"])

with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "metadata" in msg and msg["metadata"]:
                meta = msg["metadata"]
                badge_html = f"<span class='badge'>Latency: {meta.get('latency_ms', 0):.1f} ms</span>"
                if meta.get("resolution_status"):
                    status_color = "#166534" if meta.get("resolution_status") == "RESOLVED" else "#854d0e"
                    status_bg = "#dcfce7" if meta.get("resolution_status") == "RESOLVED" else "#fef9c3"
                    badge_html += f"<span class='badge' style='background-color:{status_bg};color:{status_color};'>Status: {meta.get('resolution_status')}</span>"
                if meta.get("cached"):
                    badge_html += "<span class='badge' style='background-color:#dcfce7;color:#166534;'>Cached</span>"
                badge_html += f"<span class='badge'>Provider: {meta.get('provider_used', 'custom')}</span>"
                st.markdown(badge_html, unsafe_allow_html=True)

                if meta.get("compacted_dossier"):
                    with st.expander("Compacted Evidence Dossier (Context Engineering)", expanded=False):
                        st.code(meta["compacted_dossier"], language="markdown")

                if meta.get("auditor_checks"):
                    with st.expander("Policy Auditor Verification (Independent Verifier)", expanded=False):
                        st.write(f"**Verified:** {'Yes' if meta.get('auditor_verified') else 'No'}")
                        for chk in meta["auditor_checks"]:
                            st.write(f"- {chk}")

                if meta.get("tool_calls_executed"):
                    with st.expander("Tool calls executed", expanded=False):
                        for tool in meta["tool_calls_executed"]:
                            st.json(tool)

                if meta.get("rag_sources"):
                    with st.expander(f"Retrieved context chunks ({len(meta['rag_sources'])})", expanded=False):
                        for src in meta["rag_sources"]:
                            st.markdown(f"**Chunk:** `{src.get('chunk_id')}` (source: `{src.get('metadata', {}).get('source', src.get('doc_id'))}`, score: `{src.get('score', 0):.4f}`)")
                            st.text(src.get("content"))

    if user_input := st.chat_input("Ask a question about your uploaded document, order ORD-1001, or policies..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking & Investigating..."):
                if agentic_mode:
                    from src.agentic.multi_agent import MultiAgentSystem
                    agent_sys = MultiAgentSystem()
                    trace = agent_sys.run(
                        user_query=user_input,
                        conversation_history=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[:-1]
                        ]
                    )
                    reply_text = trace.final_response
                    meta_info = {
                        "latency_ms": trace.total_latency_ms,
                        "cached": False,
                        "provider_used": "multi_agent_specialist",
                        "resolution_status": trace.resolution_status,
                        "tool_calls_executed": trace.tools_executed,
                        "compacted_dossier": trace.dossier.render_compact_context(),
                        "auditor_verified": trace.auditor_report.verified if trace.auditor_report else True,
                        "auditor_checks": trace.auditor_report.passed_checks if trace.auditor_report else []
                    }
                else:
                    from src.assistant.agent import AIAssistantAgent
                    agent = AIAssistantAgent(rag_pipeline=rag_instance if use_rag else None)
                    gen_result = agent.run(
                        user_query=user_input,
                        conversation_history=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[:-1]
                        ],
                        use_rag=use_rag,
                        use_tools=use_tools
                    )
                    reply_text = gen_result.response
                    meta_info = {
                        "latency_ms": gen_result.total_latency_ms,
                        "cached": False,
                        "provider_used": gen_result.provider_used,
                        "tool_calls_executed": gen_result.tool_calls_executed,
                        "rag_sources": gen_result.rag_sources
                    }

                st.markdown(reply_text)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply_text,
                    "metadata": meta_info
                })
                st.rerun()


with tab_kb:
    st.subheader("Knowledge Base Search & Index Status")
    st.markdown(f"**Total chunks in vector database:** `{rag_instance.store.count()}`")

    docs = rag_instance.get_documents_summary()
    if docs:
        st.write("Indexed documents:")
        st.dataframe(docs, use_container_width=True)

    search_q = st.text_input("Semantic Search Query:", value="Artificial intelligence")
    if st.button("Search Knowledge Base"):
        res = rag_instance.retrieve(search_q, top_k=5)
        if res:
            for idx, r in enumerate(res):
                st.markdown(f"**{idx+1}. Chunk ID:** `{r['chunk_id']}` (source: `{r.get('metadata', {}).get('source', r.get('doc_id'))}`, Score: `{r['score']:.4f}`)")
                st.info(r["content"])
        else:
            st.warning("No matching documents found.")

with tab_onnx:
    st.subheader("Support Intent Classifier (ONNX Runtime)")
    st.markdown("Tests the converted 11-category customer support router model exported from PyTorch.")

    sample_query = st.text_input(
        "Sample customer message:",
        value="I received a broken keyboard for order ORD-1001 and want a refund."
    )

    if st.button("Classify intent"):
        from src.optimization.onnx_infer import ONNXIntentClassifier
        classifier = ONNXIntentClassifier()
        t0 = time.perf_counter()
        result = classifier.classify_text(sample_query)
        latency = (time.perf_counter() - t0) * 1000.0

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.metric("Predicted intent", result["intent"])
            st.metric("Confidence", f"{result['confidence'] * 100:.2f}%")
            st.metric("Latency", f"{latency:.2f} ms")

        with col_r2:
            st.write("Class probabilities")
            st.bar_chart(result["probabilities"])
