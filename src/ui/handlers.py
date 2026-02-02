"""Event handlers for SQL execution, chart generation, and user input processing."""

from typing import Any, Dict, List, Optional
import streamlit as st
from src.query import run_sql_query
from src.export import generate_export
from src.charts import generate_chart
from src.llm import run_llm, format_sql_results
from src.state import add_message


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


def execute_sql_and_chart(
    sql: str,
    original_query: str,
    chart_type: str,
    x_column: str,
    y_column: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute SQL and generate chart from results."""
    try:
        result = run_sql_query(sql)
        
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error")}
        
        rows = result.get("rows") if isinstance(result, dict) else result
        rows = rows if isinstance(rows, list) else []
        
        if not rows:
            return {"error": "Query returned no results to chart."}
        
        # Sanitize rows
        def sanitize(val):
            if isinstance(val, bytes):
                try:
                    return val.decode("utf-8")
                except Exception:
                    return val.hex()
            return val
        
        safe_rows = [{k: sanitize(v) for k, v in row.items()} for row in rows]
        
        # Generate chart
        chart_result = generate_chart(
            safe_rows,
            chart_type,
            x_column,
            y_column,
            title,
            theme=st.session_state.get("chart_theme", "default"),
            color=st.session_state.get("chart_color"),
            show_grid=st.session_state.get("chart_show_grid", True),
            show_legend=st.session_state.get("chart_show_legend", False),
            font_size=st.session_state.get("chart_font_size", 10),
        )
        
        if not chart_result["success"]:
            return {"error": chart_result["error"]}
        
        return {
            "success": True,
            "rows": safe_rows,
            "chart_data": chart_result["chart_data"],
            "file_name": chart_result["file_name"],
            "mime": chart_result["mime"],
            "chart_type": chart_type,
            "title": chart_result.get("title", ""),
            "theme": chart_result.get("theme", "default"),
        }
    except Exception as e:
        return {"error": str(e)}


def regenerate_chart_with_options():
    """Regenerate the last chart with custom options from session state."""
    if not st.session_state.get("last_chart_rows"):
        return None
    
    x_col = st.session_state.get("last_chart_x_column", "")
    y_col = st.session_state.get("last_chart_y_column", "")
    
    if not x_col or not y_col:
        return None
    
    # Apply row limit to the data
    rows_to_chart = st.session_state["last_chart_rows"]
    row_limit = st.session_state.get("chart_row_limit", 25)
    
    if row_limit != "All" and isinstance(row_limit, int):
        rows_to_chart = rows_to_chart[:row_limit]
    
    chart_result = generate_chart(
        rows_to_chart,
        st.session_state.get("last_chart_type", "bar"),
        x_col,
        y_col,
        st.session_state.get("last_chart_title"),
        theme=st.session_state.get("chart_theme", "default"),
        color=st.session_state.get("chart_color"),
        show_grid=st.session_state.get("chart_show_grid", True),
        show_legend=st.session_state.get("chart_show_legend", False),
        font_size=st.session_state.get("chart_font_size", 10),
    )
    
    return chart_result if chart_result.get("success") else None


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
    
    elif response_type == "chart":
        # Chart from existing data
        add_message(
            "assistant",
            result.get("answer", "Here's your chart!"),
            chart_data=result.get("chart_data"),
            file_name=result.get("file_name"),
            file_mime=result.get("mime"),
        )
        return {"type": "chart"}
    
    elif response_type == "sql_and_chart":
        # SQL + Chart combined - store for approval
        sql = result.get("sql")
        st.session_state.pending_sql = {
            "sql": sql,
            "original_query": prompt,
            "chart_type": result.get("chart_type", "bar"),
            "x_column": result.get("x_column"),
            "y_column": result.get("y_column"),
            "title": result.get("title"),
            "auto_chart": True,
        }
        return {"type": "sql_and_chart", "sql": sql}
    
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
        auto_chart = pending.get("auto_chart", False)
        
        if auto_chart:
            # Execute SQL and auto-generate chart
            result = execute_sql_and_chart(
                sql,
                original_query,
                pending.get("chart_type", "bar"),
                pending.get("x_column"),
                pending.get("y_column"),
                pending.get("title"),
            )
            
            if result.get("error"):
                add_message("assistant", f"SQL execution failed: {result['error']}")
            else:
                st.session_state.last_results = result.get("rows", [])
                
                # Store chart parameters for customization
                st.session_state.last_chart_rows = result.get("rows", [])
                st.session_state.last_chart_type = pending.get("chart_type", "bar")
                st.session_state.last_chart_x_column = pending.get("x_column")
                st.session_state.last_chart_y_column = pending.get("y_column")
                st.session_state.last_chart_title = pending.get("title")
                
                add_message(
                    "assistant",
                    f"Here's your {result['chart_type']} chart with {len(result['rows'])} data points.",
                    chart_data=result["chart_data"],
                    file_name=result["file_name"],
                    file_mime=result["mime"],
                )
        elif auto_export:
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
