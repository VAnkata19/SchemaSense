"""
SchemaSense - SQL Ingestion Page
Upload and process SQL files to populate the vector database.
"""

import subprocess
from pathlib import Path

import streamlit as st

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(page_title="Ingestion | SchemaSense", layout="centered")

PROJECT_ROOT = Path(__file__).parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
INGESTION_SCRIPT = PROJECT_ROOT / "ingestion" / "ingestion.py"
SQL_FILE_PATH = PROJECT_ROOT / "nstnwnd.sql"

# ============================================================================
# UI
# ============================================================================

st.title("SQL Ingestion")
st.caption("Upload a SQL file to populate your vector database with table schemas.")

st.divider()

# File upload
uploaded_file = st.file_uploader(
    "Choose a SQL file",
    type=["sql"],
    help="Upload your SQL database schema file (.sql)",
)

if uploaded_file:
    st.success(f"**{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
    
    if st.button("Start Ingestion", use_container_width=True, type="primary"):
        # Save file
        with st.status("Processing...", expanded=True) as status:
            st.write("Saving SQL file...")
            SQL_FILE_PATH.write_bytes(uploaded_file.getbuffer())
            
            st.write("Running ingestion script...")
            
            try:
                result = subprocess.run(
                    [str(VENV_PYTHON), str(INGESTION_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                
                if result.returncode == 0:
                    status.update(label="Ingestion Complete!", state="complete")
                    if result.stdout:
                        st.code(result.stdout, language="")
                    st.balloons()
                else:
                    status.update(label="Ingestion Failed", state="error")
                    if result.stderr:
                        st.error(result.stderr)
                    if result.stdout:
                        st.code(result.stdout, language="")
                        
            except subprocess.TimeoutExpired:
                status.update(label="Timeout", state="error")
                st.error("Ingestion timed out after 5 minutes.")
                
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Error: {str(e)}")

else:
    st.info("Upload a SQL file to get started")

# ============================================================================
# SIDEBAR INFO
# ============================================================================

with st.sidebar:
    st.subheader("About")
    st.markdown("""
    This tool extracts **CREATE TABLE** definitions from your SQL file 
    and stores them in a vector database for semantic search.
    
    **Supported:**
    - SQLite schema files
    - CREATE TABLE statements
    - Multiple tables per file
    """)
