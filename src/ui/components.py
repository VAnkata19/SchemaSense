"""UI components for the SchemaSense chat interface."""

from typing import Any, Dict, List, Optional
import io
import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container


def render_message(msg: Dict[str, Any], idx: int):
    """Render a single chat message."""
    from src.state import add_message
    
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    file_data = msg.get("file_data")
    chart_data = msg.get("chart_data")
    
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
        
        # Display chart if present
        if chart_data:
            st.image(io.BytesIO(chart_data), use_container_width=True)
            st.download_button(
                label=f"Download {msg.get('file_name', 'chart.png')}",
                data=chart_data,
                file_name=msg.get("file_name", "chart.png"),
                mime=msg.get("file_mime", "image/png"),
                use_container_width=True,
                key=f"chart_download_{idx}",
            )
            
            # Show customization UI after chart
            render_chart_customization()
        
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


def render_chart_customization():
    """Render chart customization options."""
    from src.charts import CHART_THEMES
    
    if not st.session_state.get("last_chart_rows"):
        return
    
    with st.expander("Chart Customization", expanded=False):
        # Theme and Color
        col1, col2 = st.columns(2)
        
        with col1:
            theme = st.selectbox(
                "Theme",
                options=list(CHART_THEMES.keys()),
                index=list(CHART_THEMES.keys()).index(st.session_state.get("chart_theme", "default")),
                key="theme_select",
            )
            st.session_state.chart_theme = theme
        
        with col2:
            color = st.color_picker(
                "Custom Color",
                value=st.session_state.get("chart_color", "#4f46e5"),
                key="color_picker",
            )
            st.session_state.chart_color = color
        
        # Grid, Legend, and Font Size
        col3, col4, col5 = st.columns(3)
        
        with col3:
            show_grid = st.checkbox(
                "Show Grid",
                value=st.session_state.get("chart_show_grid", True),
                key="grid_check",
            )
            st.session_state.chart_show_grid = show_grid
        
        with col4:
            show_legend = st.checkbox(
                "Show Legend",
                value=st.session_state.get("chart_show_legend", False),
                key="legend_check",
            )
            st.session_state.chart_show_legend = show_legend
        
        with col5:
            font_size = st.slider(
                "Text Size (pt)",
                min_value=8,
                max_value=20,
                value=st.session_state.get("chart_font_size", 10),
                step=1,
                key="font_size_slider",
            )
            st.session_state.chart_font_size = font_size
        
        # Row limit selector
        st.divider()
        st.markdown("**Data Display Options**")
        
        row_limit = st.selectbox(
            "Rows to Display",
            options=[10, 25, 50, 100, 500, "All"],
            index=st.session_state.get("chart_row_limit_idx", 1),
            key="row_limit_select",
        )
        st.session_state.chart_row_limit = row_limit if row_limit == "All" else int(row_limit)
        st.session_state.chart_row_limit_idx = [10, 25, 50, 100, 500, "All"].index(row_limit)

        st.divider()
        
        if st.button("Regenerate Chart", use_container_width=True, key="regen_chart"):
            from src.ui.handlers import regenerate_chart_with_options
            new_chart = regenerate_chart_with_options()
            if new_chart:
                # Update the last message with new chart
                if st.session_state.messages:
                    st.session_state.messages[-1]["chart_data"] = new_chart["chart_data"]
                    st.session_state.messages[-1]["file_name"] = new_chart["file_name"]
                st.rerun()
            else:
                st.error("Failed to regenerate chart")
        
        # Display data table with selected columns
        if st.session_state.get("last_chart_rows"):
            st.markdown("**Data Preview**")
            
            rows_to_show = st.session_state.get("last_chart_rows", [])
            row_limit = st.session_state.get("chart_row_limit", 25)
            
            if row_limit != "All":
                rows_to_show = rows_to_show[:row_limit]
            
            # Create dataframe
            df_display = pd.DataFrame(rows_to_show)
            st.dataframe(df_display, use_container_width=True, height=300)


def render_sql_approval(
    sql: str,
    auto_export: bool = False,
    export_format: Optional[str] = None,
    auto_chart: bool = False,
    chart_type: Optional[str] = None,
):
    """Render SQL approval UI."""
    from src.ui.handlers import handle_sql_approval
    
    st.markdown("**The model wants to run this SQL:**")
    st.code(sql, language="sql")
    
    if auto_export and export_format:
        st.info(f"Will automatically export as **{export_format.upper()}** after execution")
    
    if auto_chart and chart_type:
        st.info(f"Will automatically generate a **{chart_type.upper()}** chart after execution")
    
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
