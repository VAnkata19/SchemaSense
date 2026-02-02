"""
SchemaSense - Natural Language to SQL Chat Interface
Clean, refactored implementation with proper Streamlit state management.
"""

from typing import Any, Dict, List, Optional
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from backend.core import run_llm, format_sql_results
from backend.run_sql_query import run_sql_query

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(page_title="SchemaSense", layout="centered")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "messages": [
            {
                "role": "assistant",
                "content": "Ask me questions about the company data or schema.",
            }
        ],
        "last_results": None,
        "pending_sql": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_message(role: str, content: str, **kwargs):
    """Add a message to chat history."""
    msg = {"role": role, "content": content, **kwargs}
    st.session_state.messages.append(msg)

def clear_chat():
    """Clear chat history and reset state."""
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": "Ask me questions about the company data or schema.",
        }
    ]
    st.session_state.last_results = None
    st.session_state.pending_sql = None

def execute_sql(sql: str, original_query: str) -> Optional[Dict[str, Any]]:
    """Execute SQL and return formatted results."""
    try:
        result = run_sql_query(sql)
        
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error")}
        
        rows = result.get("rows") if isinstance(result, dict) else result
        rows = rows if isinstance(rows, list) else []
        
        # Format results using LLM
        formatted = format_sql_results(original_query, sql, rows)
        
        return {
            "success": True,
            "message": formatted.get("message", "Results displayed."),
            "rows": formatted.get("rows", rows),
        }
    except Exception as e:
        return {"error": str(e)}

def execute_sql_and_export(sql: str, original_query: str, export_format: str) -> Dict[str, Any]:
    """Execute SQL, format results, and generate export file."""
    from backend.core import generate_export
    
    try:
        result = run_sql_query(sql)
        
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error")}
        
        rows = result.get("rows") if isinstance(result, dict) else result
        rows = rows if isinstance(rows, list) else []
        
        if not rows:
            return {"error": "Query returned no results to export."}
        
        # Sanitize rows
        def sanitize(val):
            if isinstance(val, bytes):
                try:
                    return val.decode("utf-8")
                except Exception:
                    return val.hex()
            return val
        
        safe_rows = [{k: sanitize(v) for k, v in row.items()} for row in rows]
        
        # Generate export
        export_result = generate_export(safe_rows, export_format)
        
        if not export_result["success"]:
            return {"error": export_result["error"]}
        
        return {
            "success": True,
            "rows": safe_rows,
            "file_data": export_result["file_data"],
            "file_name": export_result["file_name"],
            "mime": export_result["mime"],
            "format": export_format,
        }
    except Exception as e:
        return {"error": str(e)}

def process_user_input(prompt: str):
    """Process user input and generate response."""
    # Add user message
    add_message("user", prompt)
    
    # Get LLM response
    result = run_llm(prompt, st.session_state.last_results)
    response_type = result.get("type", "answer")
    
    if response_type == "export":
        # Export file response
        add_message(
            "assistant",
            result.get("answer", "Here you go!"),
            file_data=result.get("file_data"),
            file_name=result.get("file_name"),
            file_mime=result.get("mime"),
        )
        return {"type": "export"}
    
    elif response_type == "sql_and_export":
        # SQL + Export combined - store for approval
        sql = result.get("sql")
        export_format = result.get("export_format", "csv")
        st.session_state.pending_sql = {
            "sql": sql,
            "original_query": prompt,
            "export_format": export_format,
            "auto_export": True,
        }
        return {"type": "sql_and_export", "sql": sql, "format": export_format}
    
    elif response_type == "sql":
        # SQL query needs approval
        sql = result.get("sql")
        st.session_state.pending_sql = {
            "sql": sql,
            "original_query": prompt,
        }
        return {"type": "sql", "sql": sql}
    
    else:
        # Direct answer
        add_message("assistant", result.get("answer", "No answer returned."))
        return {"type": "answer"}

def handle_sql_approval(approved: bool):
    """Handle SQL approval/denial."""
    pending = st.session_state.pending_sql
    
    if not pending:
        return
    
    if approved:
        sql = pending["sql"]
        original_query = pending["original_query"]
        auto_export = pending.get("auto_export", False)
        export_format = pending.get("export_format", "csv")
        
        if auto_export:
            # Execute SQL and auto-export
            result = execute_sql_and_export(sql, original_query, export_format)
            
            if result.get("error"):
                add_message("assistant", f"SQL execution failed: {result['error']}")
            else:
                st.session_state.last_results = result.get("rows", [])
                add_message(
                    "assistant",
                    f"Here you go! Your {export_format.upper()} file with {len(result['rows'])} rows is ready.",
                    file_data=result["file_data"],
                    file_name=result["file_name"],
                    file_mime=result["mime"],
                )
        else:
            # Regular SQL execution
            result = execute_sql(sql, original_query)
            
            if result and result.get("error"):
                add_message("assistant", f"SQL execution failed: {result['error']}")
            elif result:
                st.session_state.last_results = result.get("rows", [])
                add_message("assistant", result.get("message", "Query executed."))
    else:
        add_message("assistant", "SQL execution denied.")
    
    # Clear pending
    st.session_state.pending_sql = None

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_message(msg: Dict[str, Any], idx: int):
    """Render a single chat message."""
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    file_data = msg.get("file_data")
    
    # Check for error message styling
    is_error = (
        role == "assistant" 
        and isinstance(content, str) 
        and content.startswith("SQL execution failed")
    )
    
    with st.chat_message(role):
        if is_error:
            st.error(content)
        else:
            st.markdown(content)
        
        # Download button for export messages
        if file_data:
            st.download_button(
                label=f"Download {msg.get('file_name', 'file')}",
                data=file_data,
                file_name=msg.get("file_name"),
                mime=msg.get("file_mime"),
                use_container_width=True,
                key=f"download_{idx}",
            )

def render_sql_approval(sql: str, auto_export: bool = False, export_format: Optional[str] = None):
    """Render SQL approval UI."""
    st.markdown("**The model wants to run this SQL:**")
    st.code(sql, language="sql")
    
    if auto_export and export_format:
        st.info(f"Will automatically export as **{export_format.upper()}** after execution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with stylable_container(
            "green_button",
            css_styles="""
            button {
                background-color: #16a34a;
                color: white;
                border: none;
            }
            button:hover {
                background-color: #15803d;
                color: white;
            }
            """,
        ):
            if st.button("Allow & Run", use_container_width=True):
                handle_sql_approval(True)
                st.rerun()
    
    with col2:
        with stylable_container(
            "red_button",
            css_styles="""
            button {
                background-color: #dc2626;
                color: white;
                border: none;
            }
            button:hover {
                background-color: #b91c1c;
                color: white;
            }
            """,
        ):
            if st.button("Deny", use_container_width=True):
                handle_sql_approval(False)
                st.rerun()

def render_chat_history():
    """Render all chat messages."""
    for idx, msg in enumerate(st.session_state.messages):
        render_message(msg, idx)

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
                
                if result["type"] in ("sql", "sql_and_export"):
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
                
                else:
                    # Regular answer - show it
                    last_msg = st.session_state.messages[-1]
                    st.markdown(last_msg["content"])
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
