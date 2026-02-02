"""Session state management."""

import streamlit as st


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
        # Chart customization
        "chart_theme": "default",
        "chart_color": "#4f46e5",
        "chart_show_grid": True,
        "chart_show_legend": False,
        "chart_font_size": 10,
        "chart_row_limit": 25,
        "chart_row_limit_idx": 1,
        "chart_selected_columns": [],
        # Last chart data
        "last_chart_rows": None,
        "last_chart_type": None,
        "last_chart_x_column": None,
        "last_chart_y_column": None,
        "last_chart_title": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
    st.session_state.last_chart_rows = None
