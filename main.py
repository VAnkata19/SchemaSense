"""
SchemaSense - Natural Language to SQL Chat Interface
Modular implementation with clean separation of concerns.
"""

import io
import streamlit as st

from src.state import init_session_state, clear_chat
from src.ui import (
    render_chat_history,
    render_sql_approval,
    process_user_input,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(page_title="SchemaSense", layout="centered")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

init_session_state()


# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.title("SchemaSense")

# Sidebar
with st.sidebar:
    st.subheader("Settings")
    if st.button("Clear Chat", use_container_width=True):
        clear_chat()
        st.rerun()
    
    st.divider()
    st.caption("Ask questions about your data in natural language.")

# Render chat history
render_chat_history()

# Pending SQL approval
if st.session_state.pending_sql:
    pending = st.session_state.pending_sql
    render_sql_approval(
        pending["sql"],
        auto_export=pending.get("auto_export", False),
        export_format=pending.get("export_format"),
        auto_chart=pending.get("auto_chart", False),
        chart_type=pending.get("chart_type"),
    )

# Chat input
if prompt := st.chat_input("Ask a question (e.g., 'show me all categories')"):
    # Clear any pending SQL when new prompt comes in
    if st.session_state.pending_sql:
        st.session_state.pending_sql = None
    
    # Show user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process and show assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = process_user_input(prompt)
                
                if result["type"] in ("sql", "sql_and_export", "sql_and_chart"):
                    # SQL needs approval - rerun to show approval UI
                    st.rerun()
                
                elif result["type"] == "export":
                    # Get the last message (the export message we just added)
                    last_msg = st.session_state.messages[-1]
                    st.markdown(last_msg["content"])
                    if last_msg.get("file_data"):
                        st.download_button(
                            label=f"Download {last_msg.get('file_name', 'file')}",
                            data=last_msg["file_data"],
                            file_name=last_msg["file_name"],
                            mime=last_msg["file_mime"],
                            use_container_width=True,
                        )
                
                elif result["type"] == "chart":
                    # Chart from existing data - display it
                    last_msg = st.session_state.messages[-1]
                    st.markdown(last_msg["content"])
                    if last_msg.get("chart_data"):
                        st.image(io.BytesIO(last_msg["chart_data"]), use_container_width=True)
                        st.download_button(
                            label=f"Download {last_msg.get('file_name', 'chart.png')}",
                            data=last_msg["chart_data"],
                            file_name=last_msg.get("file_name", "chart.png"),
                            mime=last_msg.get("file_mime", "image/png"),
                            use_container_width=True,
                        )
                
                else:
                    # Regular answer - show it
                    last_msg = st.session_state.messages[-1]
                    st.markdown(last_msg["content"])
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
