import os
import sys
import json
import time
import uuid
import datetime
from pathlib import Path
import streamlit as st
from app import ask

# Base file paths
BASE_DIR = Path(__file__).resolve().parent
CHATS_FILE = BASE_DIR / "chats.json"

# Configure Page
st.set_page_config(
    page_title="Orient BlackSwan History Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Persistence Helpers (chats.json)
# -------------------------------------------------------------
def load_chats_store():
    if not CHATS_FILE.exists():
        default_id = str(uuid.uuid4())
        initial_data = {
            "active_chat_id": default_id,
            "chats": [
                {
                    "id": default_id,
                    "title": "New chat",
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "messages": []
                }
            ]
        }
        save_chats_store(initial_data)
        return initial_data

    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data.get("chats"):
                default_id = str(uuid.uuid4())
                data = {
                    "active_chat_id": default_id,
                    "chats": [{
                        "id": default_id,
                        "title": "New chat",
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "messages": []
                    }]
                }
                save_chats_store(data)
            return data
    except Exception:
        default_id = str(uuid.uuid4())
        return {
            "active_chat_id": default_id,
            "chats": [{
                "id": default_id,
                "title": "New chat",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messages": []
            }]
        }

def save_chats_store(data):
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving chats.json: {e}")

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
if "store" not in st.session_state:
    st.session_state["store"] = load_chats_store()

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

if "is_generating" not in st.session_state:
    st.session_state["is_generating"] = False

if "stop_requested" not in st.session_state:
    st.session_state["stop_requested"] = False

store = st.session_state["store"]
active_chat_id = store.get("active_chat_id")
active_chat = next((c for c in store["chats"] if c["id"] == active_chat_id), None)
if not active_chat:
    active_chat = store["chats"][0]
    store["active_chat_id"] = active_chat["id"]

# -------------------------------------------------------------
# Theme & CSS Styling (ChatGPT Dark / Light)
# -------------------------------------------------------------
is_dark = st.session_state["theme"] == "dark"

bg_color = "#212121" if is_dark else "#ffffff"
sidebar_bg = "#171717" if is_dark else "#f9f9f9"
card_bg = "#2f2f2f" if is_dark else "#f3f4f6"
text_color = "#ececec" if is_dark else "#111827"
subtext_color = "#9ca3af" if is_dark else "#6b7280"
user_bubble_bg = "#2f2f2f" if is_dark else "#f3f4f6"
bot_bubble_bg = "#212121" if is_dark else "#ffffff"
border_color = "#383838" if is_dark else "#e5e7eb"
active_chat_bg = "#262626" if is_dark else "#e5e7eb"

st.markdown(f"""
<style>
    /* Hide Streamlit UI Chrome */
    #MainMenu {{ visibility: hidden !important; }}
    footer {{ visibility: hidden !important; }}
    .stDeployButton {{ display: none !important; }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}

    /* Main Container */
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    /* Center Content Container */
    .block-container {{
        max-width: 820px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 7rem !important;
        margin: 0 auto !important;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
        gap: 0.4rem;
    }}

    /* New Chat Button */
    .stButton > button[kind="primary"] {{
        background-color: #10a37f !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}

    /* Chat item link */
    .chat-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        background-color: transparent;
        color: {text_color};
        cursor: pointer;
        font-size: 0.9rem;
        border: 1px solid transparent;
        text-decoration: none;
    }}
    .chat-item:hover {{
        background-color: {card_bg};
    }}
    .chat-item.active {{
        background-color: {active_chat_bg};
        border-color: {border_color};
        font-weight: 600;
    }}

    /* Welcome Cards */
    .welcome-container {{
        text-align: center;
        padding: 40px 10px 20px 10px;
    }}
    .welcome-title {{
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 8px;
        color: {text_color};
    }}
    .welcome-subtitle {{
        font-size: 1.05rem;
        color: {subtext_color};
        margin-bottom: 30px;
    }}
    .suggestion-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 14px 18px;
        text-align: left;
        color: {text_color};
        font-size: 0.92rem;
        margin-bottom: 10px;
        transition: all 0.2s ease;
        cursor: pointer;
    }}
    .suggestion-card:hover {{
        border-color: #10a37f;
        transform: translateY(-1px);
    }}

    /* Message Bubbles */
    .msg-user-box {{
        display: flex;
        justify-content: flex-end;
        margin-bottom: 24px;
    }}
    .msg-user {{
        background-color: {user_bubble_bg};
        border: 1px solid {border_color};
        color: {text_color};
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        font-size: 1.02rem;
        line-height: 1.5;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }}

    .msg-bot-box {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 28px;
    }}
    .bot-avatar {{
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background-color: #10a37f;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 16px;
        flex-shrink: 0;
        margin-top: 2px;
    }}
    .msg-bot {{
        flex: 1;
        background-color: {bot_bubble_bg};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}
    .bot-answer-text {{
        font-size: 1.12rem;
        font-weight: 500;
        line-height: 1.55;
        margin-bottom: 12px;
        color: {text_color};
    }}

    /* Badges */
    .tag-found {{
        display: inline-flex;
        align-items: center;
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
    }}
    .tag-notfound {{
        display: inline-flex;
        align-items: center;
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
    }}
    .badge-page {{
        display: inline-flex;
        align-items: center;
        background-color: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 0.82rem;
        font-weight: 600;
    }}

    /* Action Row */
    .action-row {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 14px;
        padding-top: 10px;
        border-top: 1px solid {border_color};
        font-size: 0.82rem;
        color: {subtext_color};
    }}

    /* Stopped Message */
    .msg-stopped {{
        color: #94a3b8;
        font-style: italic;
        padding: 8px 14px;
        background: {card_bg};
        border-radius: 8px;
        border-left: 3px solid #ef4444;
        margin: 10px 0 20px 0;
    }}

    /* Chat Input Bar fixed */
    .stChatInput {{
        max-width: 820px !important;
        margin: 0 auto !important;
    }}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Top Right Header Tools (Theme Toggle)
# -------------------------------------------------------------
col_space, col_theme = st.columns([12, 1])
with col_theme:
    theme_icon = "☀️" if is_dark else "🌙"
    if st.button(theme_icon, help="Toggle Light / Dark mode", key="btn_theme_toggle"):
        st.session_state["theme"] = "light" if is_dark else "dark"
        st.rerun()

# -------------------------------------------------------------
# Sidebar: ChatGPT Style
# -------------------------------------------------------------
with st.sidebar:
    # 1. New Chat Button
    if st.button("➕  New chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        new_chat = {
            "id": new_id,
            "title": "New chat",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": []
        }
        store["chats"].insert(0, new_chat)
        store["active_chat_id"] = new_id
        save_chats_store(store)
        st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.caption("RECENT CONVERSATIONS")

    # 2. Scrollable Chat History List (Newest first)
    chat_to_delete = None
    for chat in store["chats"]:
        cid = chat["id"]
        is_active = (cid == active_chat_id)
        chat_title = chat.get("title", "New chat")
        display_title = (chat_title[:28] + "...") if len(chat_title) > 28 else chat_title
        
        c_btn, c_menu = st.columns([5, 1])
        with c_btn:
            btn_style = "active" if is_active else "normal"
            if st.button(
                f"💬 {display_title}",
                key=f"sel_chat_{cid}",
                use_container_width=True,
                help=chat_title
            ):
                store["active_chat_id"] = cid
                save_chats_store(store)
                st.rerun()

        with c_menu:
            with st.popover("⋮", help="Chat options"):
                st.write(f"**{chat_title}**")
                new_title = st.text_input("Rename title", value=chat_title, key=f"rename_input_{cid}")
                if st.button("Save Name", key=f"save_rename_{cid}"):
                    if new_title.strip():
                        chat["title"] = new_title.strip()
                        save_chats_store(store)
                        st.rerun()
                
                st.divider()
                if st.button("🗑️ Delete Chat", key=f"del_btn_{cid}"):
                    chat_to_delete = cid

    if chat_to_delete:
        store["chats"] = [c for c in store["chats"] if c["id"] != chat_to_delete]
        if not store["chats"]:
            default_id = str(uuid.uuid4())
            store["chats"] = [{
                "id": default_id,
                "title": "New chat",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messages": []
            }]
            store["active_chat_id"] = default_id
        elif store["active_chat_id"] == chat_to_delete:
            store["active_chat_id"] = store["chats"][0]["id"]
        save_chats_store(store)
        st.rerun()

    st.markdown("<div style='flex-grow: 1; height: 30px;'></div>", unsafe_allow_html=True)
    st.divider()

    # 3. Export Chat as Markdown
    if active_chat and active_chat.get("messages"):
        export_md = f"# {active_chat.get('title', 'Chat Export')}\n\n"
        for m in active_chat["messages"]:
            if m["role"] == "user":
                export_md += f"**User**: {m['content']}\n\n"
            else:
                export_md += f"**Bot**: {m.get('answer', '')}\n"
                export_md += f"*Reference*: {m.get('pages', 'N/A')}\n\n"
        st.download_button(
            "📥 Export Chat (Markdown)",
            data=export_md,
            file_name=f"chat_{active_chat_id[:8]}.md",
            mime="text/markdown",
            use_container_width=True
        )

    # 4. Clear All Chats (with confirmation)
    with st.popover("🗑️ Clear all chats", use_container_width=True):
        st.warning("Are you sure you want to delete all chat history?")
        if st.button("Yes, Clear Everything", type="primary"):
            default_id = str(uuid.uuid4())
            store["chats"] = [{
                "id": default_id,
                "title": "New chat",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messages": []
            }]
            store["active_chat_id"] = default_id
            save_chats_store(store)
            st.rerun()

    # 5. Settings Expander
    with st.expander("⚙️ Settings"):
        current_provider = os.getenv("LLM_PROVIDER", "google").lower()
        provider_options = ["Google Gemini", "Groq"]
        default_idx = 0 if current_provider == "google" else 1
        chosen_provider = st.selectbox("LLM Provider", provider_options, index=default_idx)
        if chosen_provider == "Google Gemini":
            os.environ["LLM_PROVIDER"] = "google"
        else:
            os.environ["LLM_PROVIDER"] = "groq"

    # 6. Tiny Footer
    st.caption("Orient BlackSwan History Catalogue 2024-25 · 960 chunks indexed")

# -------------------------------------------------------------
# Main Chat Area
# -------------------------------------------------------------
messages = active_chat.get("messages", [])

# Handle empty chat welcome screen
if not messages and not st.session_state["is_generating"]:
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-title">Orient BlackSwan History Bot</div>
        <div class="welcome-subtitle">Ask anything about the History catalogue 2024-25</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='font-size: 0.88rem; color: #9ca3af; margin-bottom: 12px; font-weight: 600;'>TRY ASKING:</p>", unsafe_allow_html=True)

    exam_questions = [
        "On what date were the prices in this catalogue last updated?",
        "In which year was the publisher (Orient BlackSwan) incorporated?",
        "What is the price of a Physics textbook?",
        "Who is the current Minister of Education?",
        'Which is the "best" history book for a beginner?'
    ]

    for q_idx, eq in enumerate(exam_questions, 1):
        if st.button(f"💡 {eq}", key=f"sugg_{q_idx}", use_container_width=True):
            st.session_state["pending_input"] = eq
            st.rerun()

# Render Chat Messages
for m_idx, msg in enumerate(messages):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg-user-box">
            <div class="msg-user">{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)
    elif msg["role"] == "assistant":
        is_found = (msg.get("answer", "") != "Not found")
        ans_text = msg.get("answer", "")
        pages_ref = msg.get("pages", "N/A")
        snippet = msg.get("snippet", "N/A")
        elapsed = msg.get("elapsed", "")
        msg_time = msg.get("timestamp", "")

        badge_html = ""
        if is_found:
            badge_html = f'<span class="tag-found">✓ Found in document</span> <span class="badge-page">📌 {pages_ref}</span>'
        else:
            badge_html = '<span class="tag-notfound">⚠️ Not found</span>'

        st.markdown(f"""
        <div class="msg-bot-box">
            <div class="bot-avatar">🤖</div>
            <div class="msg-bot">
                <div style="margin-bottom: 8px;">{badge_html}</div>
                <div class="bot-answer-text">{ans_text}</div>
        """, unsafe_allow_html=True)

        # Supporting snippet expander (collapsed by default)
        if is_found and snippet and snippet != "N/A":
            with st.expander("📄 Supporting snippet", expanded=False):
                st.info(snippet)

        # Action row
        col_act1, col_act2, col_act3, col_act4 = st.columns([3, 1, 1, 3])
        with col_act1:
            if elapsed:
                st.caption(f"⏱️ {elapsed} · {msg_time}")
        with col_act2:
            if st.button("📋 Copy", key=f"copy_{m_idx}"):
                st.toast("Copied answer to clipboard!")
        with col_act3:
            if st.button("🔄 Retry", key=f"regen_{m_idx}"):
                # Find preceding user question
                prev_user_q = None
                for i in range(m_idx - 1, -1, -1):
                    if messages[i]["role"] == "user":
                        prev_user_q = messages[i]["content"]
                        break
                if prev_user_q:
                    # Remove this bot reply
                    active_chat["messages"].pop(m_idx)
                    st.session_state["pending_input"] = prev_user_q
                    save_chats_store(store)
                    st.rerun()
        with col_act4:
            f_col1, f_col2 = st.columns([1, 1])
            with f_col1:
                if st.button("👍", key=f"thumb_up_{m_idx}"):
                    st.toast("Thank you for your feedback!")
            with f_col2:
                if st.button("👎", key=f"thumb_down_{m_idx}"):
                    st.toast("Feedback recorded.")

        st.markdown("</div></div>", unsafe_allow_html=True)

    elif msg["role"] == "stopped":
        st.markdown(f"""
        <div class="msg-stopped">🛑 Generation stopped by user.</div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Input Handling & Execution with Stop Button
# -------------------------------------------------------------
pending = st.session_state.pop("pending_input", None)
chat_input = st.chat_input("Ask a question about the History catalogue...")
user_query = pending or chat_input

# Check if query submitted
if user_query and user_query.strip():
    query_str = user_query.strip()
    now_time = datetime.datetime.now().strftime("%H:%M")

    # Add user message
    messages.append({
        "role": "user",
        "content": query_str,
        "timestamp": now_time
    })

    # Auto-title chat from first question
    if len(messages) == 1 or active_chat.get("title") == "New chat":
        active_chat["title"] = query_str[:30] + ("..." if len(query_str) > 30 else "")

    save_chats_store(store)
    st.session_state["is_generating"] = True
    st.session_state["stop_requested"] = False
    st.rerun()

# Generating State
if st.session_state.get("is_generating"):
    last_user_msg = messages[-1]["content"] if messages else ""

    # Stop button placed visibly above/near input
    col_stop, _ = st.columns([2, 8])
    with col_stop:
        if st.button("🛑 Stop Generation", type="primary", use_container_width=True):
            st.session_state["is_generating"] = False
            st.session_state["stop_requested"] = True
            messages.append({"role": "stopped"})
            save_chats_store(store)
            st.rerun()

    # Worker execution
    with st.spinner("Searching the catalogue..."):
        start_t = time.time()
        try:
            res = ask(last_user_msg)
            elapsed_sec = round(time.time() - start_t, 2)
            elapsed_str = f"{elapsed_sec}s"
            now_time = datetime.datetime.now().strftime("%H:%M")

            # Check if stop was pressed in the meantime
            if not st.session_state.get("stop_requested"):
                messages.append({
                    "role": "assistant",
                    "answer": res["answer"],
                    "pages": res["pages"],
                    "snippet": res["snippet"],
                    "elapsed": elapsed_str,
                    "timestamp": now_time
                })
                save_chats_store(store)
        except Exception as e:
            messages.append({
                "role": "assistant",
                "answer": f"Error: Unable to process query ({e}). Please verify your API key in .env and retry.",
                "pages": "N/A",
                "snippet": "N/A",
                "elapsed": "0s",
                "timestamp": datetime.datetime.now().strftime("%H:%M")
            })
            save_chats_store(store)
        finally:
            st.session_state["is_generating"] = False
            st.session_state["stop_requested"] = False
            st.rerun()
