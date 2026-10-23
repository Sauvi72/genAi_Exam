import os
import streamlit as st
from app import ask, get_vectorstore, PDF_PATH

# Configure Page
st.set_page_config(
    page_title="Orient BlackSwan History Bot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern polished styling
st.markdown("""
<style>
    /* Gradient Header */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
        padding: 24px 32px;
        border-radius: 14px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    .main-header h1 {
        color: white;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 6px 0;
    }
    .main-header p {
        color: #e0f2fe;
        font-size: 1.05rem;
        margin: 0;
    }

    /* Badges */
    .badge-found {
        display: inline-block;
        background-color: #dcfce7;
        color: #166534;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 20px;
        margin-bottom: 8px;
        border: 1px solid #bbf7d0;
    }
    .badge-notfound {
        display: inline-block;
        background-color: #fef3c7;
        color: #92400e;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 20px;
        margin-bottom: 8px;
        border: 1px solid #fde68a;
    }
    .badge-ref {
        display: inline-block;
        background-color: #f1f5f9;
        color: #334155;
        font-size: 0.9rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
        margin-top: 6px;
        margin-bottom: 10px;
    }

    /* Answer Text */
    .answer-text {
        font-size: 1.18rem;
        font-weight: 500;
        color: #1e293b;
        margin: 4px 0 8px 0;
        line-height: 1.5;
    }

    /* Sidebar cards */
    .sidebar-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 14px;
        border-radius: 10px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("""
<div class="main-header">
    <h1>Orient BlackSwan History Bot</h1>
    <p>Ask questions about the Orient BlackSwan History catalogue 2024-25</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Architecture & Status")
    
    # Document Info
    st.markdown("""
    <div class="sidebar-card">
        <strong>📄 Indexed Source:</strong><br/>
        <code>History_2024-25.pdf</code> (91 pages)<br/><br/>
        <strong>📊 Vector Index:</strong><br/>
        <code>ChromaDB (960 chunks)</code><br/><br/>
        <strong>🤖 Embeddings & LLM:</strong><br/>
        <code>all-MiniLM-L6-v2 + Gemini</code>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("🔄 How It Works")
    st.markdown("""
    1. **PDF**: Loaded with 1-based page indices
    2. **Chunks**: Split into 800-char segments
    3. **Embeddings**: Local MiniLM-L6-v2
    4. **ChromaDB**: Persisted vectorstore
    5. **Retriever**: Score threshold filtering
    6. **LLM**: Strict JSON prompt (`source_ids`)
    7. **UI**: Verified answer & page badge
    """)

    st.divider()

    st.subheader("💡 Example Exam Questions")
    example_questions = [
        "On what date were the prices in this catalogue last updated?",
        "In which year was the publisher (Orient BlackSwan) incorporated?",
        "What is the price of a Physics textbook?",
        "Who is the current Minister of Education?",
        'Which is the "best" history book for a beginner?'
    ]

    for idx, eq in enumerate(example_questions, 1):
        if st.button(f"Q{idx}: {eq[:38]}...", key=f"btn_q_{idx}", use_container_width=True):
            st.session_state["pending_prompt"] = eq

    st.divider()

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        if "pending_prompt" in st.session_state:
            del st.session_state["pending_prompt"]
        st.rerun()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display Messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(f"**{msg['content']}**")
        else:
            is_found = msg.get("answer", "") != "Not found"
            
            # Status Tag
            if is_found:
                st.markdown('<div class="badge-found">✅ Found in document</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="badge-notfound">⚠️ Not found</div>', unsafe_allow_html=True)

            # Answer
            st.markdown(f'<div class="answer-text">{msg["answer"]}</div>', unsafe_allow_html=True)

            # Reference Badge
            st.markdown(f'<div class="badge-ref">📌 Reference: {msg["pages"]}</div>', unsafe_allow_html=True)

            # Snippet expander if found
            if is_found and msg.get("snippet") and msg["snippet"] != "N/A":
                with st.expander("📄 Supporting snippet", expanded=False):
                    st.info(msg["snippet"])

# Check for query param or pending prompt from sidebar button
prompt = None
query_params = st.query_params
if "q" in query_params:
    prompt = query_params["q"]
    del st.query_params["q"]
elif "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

chat_input_val = st.chat_input("Ask a question about the History catalogue...")
if chat_input_val:
    prompt = chat_input_val

# Process Prompt
if prompt:
    # 1. Add and render User message
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f"**{prompt}**")

    # 2. Add and render Assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching the catalogue..."):
            res = ask(prompt)

        is_found = res["answer"] != "Not found"

        if is_found:
            st.markdown('<div class="badge-found">✅ Found in document</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="badge-notfound">⚠️ Not found</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="answer-text">{res["answer"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="badge-ref">📌 Reference: {res["pages"]}</div>', unsafe_allow_html=True)

        if is_found and res["snippet"] != "N/A":
            with st.expander("📄 Supporting snippet", expanded=True):
                st.info(res["snippet"])

        # Save to session state
        st.session_state["messages"].append({
            "role": "assistant",
            "answer": res["answer"],
            "pages": res["pages"],
            "snippet": res["snippet"]
        })
