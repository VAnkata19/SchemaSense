from typing import Any, Dict, List
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from backend.core import run_llm, format_sql_results
from backend.run_sql_query import run_sql_query
from html import escape

def _format_sources(context_docs: List[Any]) -> List[str]:
    return [
        str((meta.get("source") or "unknown"))
        for doc in (context_docs or [])
        if (meta := (getattr(doc, "metadata", None) or {})) is not None
    ]

st.set_page_config(page_title="SchemaSense", layout="centered")
st.title("SchemaSense")

with st.sidebar:
    st.subheader("Configuration")
    if st.button("Clear chat history", use_container_width=True):
        st.session_state.pop("messages", None)
        st.session_state.pop("pending_result", None)
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me questions about the company data or schema.",
            "sources": []
        }
    ]

if "pending_result" not in st.session_state:
    st.session_state.pending_result = None

if "executing_query" not in st.session_state:
    st.session_state.executing_query = False

# Display chat history
for msg in st.session_state.messages:
    content = msg.get("content", "")
    role = msg.get("role", "assistant")

    # If this assistant message indicates a SQL execution failure, render entire chat bubble with red border
    if role == "assistant" and isinstance(content, str) and content.strip().startswith("SQL execution failed"):
        with stylable_container(
            "sql_error_msg",
            css_styles="""
            [data-testid="stChatMessage"] {
                border: 3px solid #dc2626 !important;
                background-color: #ff5656 !important;
            }
            """,
        ):
            with st.chat_message(role):
                st.markdown(content)
    else:
        with st.chat_message(role):
            st.markdown(content)

# Initialize pending_result if not present
if "pending_result" not in st.session_state:
    st.session_state.pending_result = None

# STEP 1: Process new user prompt
prompt = st.chat_input("Ask a question (e.g. 'give me customers only data')")
if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "sources": []}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                result: Dict[str, Any] = run_llm(prompt)

            response_type = result.get("type", "answer")
            answer = result.get("answer", "")
            sources = _format_sources(result.get("content", []))
            sql = result.get("sql")

            # CASE 1: Direct answer
            if response_type == "answer":
                st.markdown(answer or "No answer returned.")

                # sources are intentionally not displayed on the page

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    }
                )

            # CASE 2: SQL query - store for user approval
            elif response_type == "sql" and sql:
                st.session_state.pending_result = {
                    "sql": sql,
                    "sources": sources,
                    "original_query": prompt,  # Store the original user query
                }

        except Exception as e:
            st.error("Failed to generate response")
            st.exception(e)
            import traceback
            traceback.print_exc()

# STEP 2: Handle executing state first (before rendering any buttons)
if st.session_state.executing_query:
    pending = st.session_state.get("pending_result")
    if pending and pending.get("sql"):
        sql = pending.get("sql")
        sources = pending.get("sources", [])
        original_query = pending.get("original_query", "")

        st.markdown("**Executing SQL query...**")
        st.code(sql, language="sql")

        try:
            # STEP 2A: Run query with spinner
            with st.spinner("Running query..."):
                result = run_sql_query(sql)

            # If the runner returned an error, display it on the page
            if isinstance(result, dict) and result.get("error"):
                err = result.get("error")
                st.error(f"SQL execution failed: {err}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"SQL execution failed: {err}",
                        "sources": sources,
                    }
                )
            else:
                rows = result.get("rows") if isinstance(result, dict) else result

                # STEP 2B: Format results with spinner
                with st.spinner("Formatting results..."):
                    formatted_response = format_sql_results(original_query, sql, rows)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": formatted_response,
                        "sources": sources,
                    }
                )

        except Exception as e:
            st.error("Unexpected error during SQL execution")
            st.exception(e)
            import traceback
            traceback.print_exc()

        # Clear states and rerun to show result in chat
        st.session_state.pending_result = None
        st.session_state.executing_query = False
        st.rerun()

# STEP 3: Display pending SQL and buttons (only if NOT executing)
elif st.session_state.get("pending_result") and st.session_state.pending_result.get("sql"):
    pending = st.session_state.pending_result
    sql = pending.get("sql")

    st.markdown("The model wants to run this SQL:")
    st.code(sql, language="sql")

    col1, col2 = st.columns(2)

    with col1:
        with stylable_container(
            "allow_pending",
            css_styles="""
            button {
                background-color: #16a34a;
                color: #ffffff;
                border: none;
                font-weight: bold;
            }
            """,
        ):
            allow_pending = st.button("Allow & Run", use_container_width=True, key="allow_pending")

    with col2:
        with stylable_container(
            "deny_pending",
            css_styles="""
            button {
                background-color: #dc2626;
                color: #ffffff;
                border: none;
                font-weight: bold;
            }
            """,
        ):
            deny_pending = st.button("Deny", use_container_width=True, key="deny_pending")

    if allow_pending:
        # Set flag and rerun - work will be done on next rerun
        st.session_state.executing_query = True
        st.rerun()

    if deny_pending:
        st.warning("SQL execution denied by user.")
        st.session_state.pending_result = None
        st.rerun()
