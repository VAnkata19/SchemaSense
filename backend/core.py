"""
SchemaSense Core - LLM with Tool Calling for Exports
"""

import json
import csv
import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

# ============================================================================
# CONFIGURATION
# ============================================================================

load_dotenv()

EXPORTS_DIR = Path(__file__).parent.parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# ============================================================================
# INITIALIZATION
# ============================================================================

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    show_progress_bar=False,
    chunk_size=50,
    retry_min_seconds=10,
)

vector_store = PineconeVectorStore(
    index_name=os.getenv("INDEX_NAME"),
    embedding=embeddings,
)

chat_model = init_chat_model(
    model="gpt-5.2",
    model_provider="openai",
)

# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_to_csv(rows: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """Export query results to CSV file."""
    if not rows:
        raise ValueError("No data to export")
    
    filename = filename or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = EXPORTS_DIR / filename
    
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    return str(filepath)


def export_to_excel(rows: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """Export query results to Excel file."""
    if not rows:
        raise ValueError("No data to export")
    
    filename = filename or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = EXPORTS_DIR / filename
    
    pd.DataFrame(rows).to_excel(filepath, index=False, engine="openpyxl")
    return str(filepath)


def export_to_pdf(rows: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """Export query results to PDF file."""
    if not rows:
        raise ValueError("No data to export")
    
    filename = filename or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = EXPORTS_DIR / filename
    df = pd.DataFrame(rows)
    
    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        
        page_size = landscape(letter) if len(df.columns) > 6 else letter
        doc = SimpleDocTemplate(str(filepath), pagesize=page_size)
        
        data = [list(df.columns)] + df.values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements = [
            Paragraph("Query Results", getSampleStyleSheet()["Title"]),
            Spacer(1, 0.3 * inch),
            table,
        ]
        doc.build(elements)
        
    except ImportError:
        html_path = filepath.with_suffix(".html")
        df.to_html(html_path, index=False)
        return str(html_path)
    
    return str(filepath)


def generate_export(rows: List[Dict[str, Any]], fmt: str) -> Dict[str, Any]:
    """Generate export file and return file data."""
    if not rows:
        return {"success": False, "error": "No data to export"}
    
    try:
        exporters = {
            "csv": (export_to_csv, "text/csv"),
            "excel": (export_to_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "pdf": (export_to_pdf, "application/pdf"),
        }
        
        if fmt not in exporters:
            return {"success": False, "error": f"Unknown format: {fmt}"}
        
        export_fn, mime = exporters[fmt]
        filepath = export_fn(rows)
        
        if filepath.endswith(".html"):
            mime = "text/html"
        
        with open(filepath, "rb") as f:
            file_data = f.read()
        
        return {
            "success": True,
            "file_data": file_data,
            "file_name": Path(filepath).name,
            "mime": mime,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# TOOL DEFINITIONS FOR LLM
# ============================================================================

EXPORT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "export_data",
            "description": "Export the current query results to a downloadable file. Use this when the user asks to save, download, or export data as CSV, Excel, or PDF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["csv", "excel", "pdf"],
                        "description": "The file format to export to. CSV for spreadsheet data, Excel for formatted spreadsheets, PDF for printable documents."
                    }
                },
                "required": ["format"]
            }
        }
    }
]

# ============================================================================
# LLM HELPER
# ============================================================================

def _get_llm_response(content: Any) -> str:
    """Extract string content from LLM response."""
    if isinstance(content, list):
        return str(content[0]) if content else ""
    return str(content)


# ============================================================================
# MAIN LLM FUNCTION
# ============================================================================

def run_llm(query: str, last_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Process user query using LLM with tool calling for exports.
    
    The LLM decides whether to:
    1. Generate SQL for data queries
    2. Call export_data tool for export requests
    3. Generate SQL AND export in one go
    4. Provide a direct answer
    """
    # Retrieve schema context
    docs = vector_store.as_retriever(k=4).invoke(query)
    schema_context = "\n\n".join(doc.page_content for doc in docs)
    
    # Build system prompt
    has_data = bool(last_results)
    
    system_prompt = f"""You are an expert SQLite SQL generator and data assistant.

You MUST respond in valid JSON only. No markdown, no explanations outside JSON.

For data queries, respond with:
{{"type": "sql", "sql": "<SELECT QUERY>"}}

For data queries where the user ALSO wants to export/download the results (e.g., "give me categories as CSV", "show products and export as PDF"), respond with:
{{"type": "sql_and_export", "sql": "<SELECT QUERY>", "format": "csv" | "excel" | "pdf"}}

{"For export requests when you already have data, respond with:" if has_data else ""}
{'{{"type": "export", "format": "csv" | "excel" | "pdf"}}' if has_data else ""}

For questions or impossible queries, respond with:
{{"type": "message", "content": "<response>"}}

Rules:
- Use ONLY tables/columns from the provided schema
- SQL must be SELECT-only and SQLite compatible  
- Never invent tables or columns
- If user asks for data AND wants to download/export/save it, use "sql_and_export" type
- Supported export formats: csv, excel, pdf"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Schema:\n{schema_context}\n\nQuestion: {query}"},
    ]
    
    response = chat_model.invoke(messages)
    raw = _get_llm_response(response.content).strip()
    
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "answer", "answer": raw, "content": docs}
    
    resp_type = parsed.get("type")
    
    # Handle export request when we have data
    if resp_type == "export" and has_data:
        fmt = parsed.get("format", "csv")
        result = generate_export(last_results, fmt)
        if result["success"]:
            return {
                "type": "export",
                "answer": f"Here you go! Your {fmt.upper()} file is ready.",
                "file_data": result["file_data"],
                "file_name": result["file_name"],
                "mime": result["mime"],
            }
        return {
            "type": "answer",
            "answer": f"Sorry, I couldn't generate the file: {result['error']}",
        }
    
    # Handle SQL + export combined request
    if resp_type == "sql_and_export":
        return {
            "type": "sql_and_export",
            "sql": parsed.get("sql"),
            "export_format": parsed.get("format", "csv"),
            "content": docs,
        }
    
    # Handle regular SQL request
    if resp_type == "sql":
        return {
            "type": "sql",
            "sql": parsed.get("sql"),
            "content": docs,
        }
    
    return {
        "type": "answer",
        "answer": parsed.get("content", raw),
        "content": docs,
    }


# ============================================================================
# FORMAT SQL RESULTS
# ============================================================================

def format_sql_results(original_query: str, sql: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format SQL results using LLM for natural language presentation."""
    if not rows:
        return {"message": "The query returned no results.", "rows": []}
    
    def sanitize(val):
        if isinstance(val, bytes):
            try:
                return val.decode("utf-8")
            except Exception:
                return val.hex()
        return val
    
    safe_rows = [{k: sanitize(v) for k, v in row.items()} for row in rows]
    
    system_prompt = """You are a helpful data analyst. Present the query results clearly and conversationally.
Always end by asking: "Would you like me to save this as CSV, Excel, or PDF?"
Do NOT respond in JSON - just write a natural message."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Question: {original_query}\nSQL: {sql}\nResults ({len(rows)} rows):\n{json.dumps(safe_rows, indent=2)}"},
    ]
    
    response = chat_model.invoke(messages)
    message = _get_llm_response(response.content).strip()
    
    return {"message": message, "rows": safe_rows}


# ============================================================================
# DEBUG / TESTING
# ============================================================================

if __name__ == "__main__":
    result = run_llm("show me all categories")
    print(result)
