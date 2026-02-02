"""
SchemaSense Core - LLM with Tool Calling for Exports and Charts
"""

import json
import csv
import os
import io
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
# CHART THEMES
# ============================================================================

CHART_THEMES = {
    "default": {
        "color": "#4f46e5",
        "background_color": "white",
        "grid": True,
        "legend": False,
        "font_size": 10,
        "title_size": 14,
    },
    "dark": {
        "color": "#60a5fa",
        "background_color": "#1f2937",
        "grid": True,
        "legend": False,
        "font_size": 10,
        "title_size": 14,
    },
    "professional": {
        "color": "#1e40af",
        "background_color": "#f9fafb",
        "grid": True,
        "legend": True,
        "font_size": 9,
        "title_size": 12,
    },
    "colorful": {
        "color": "#ec4899",
        "background_color": "white",
        "grid": False,
        "legend": True,
        "font_size": 10,
        "title_size": 14,
    },
}

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
# CHART GENERATION
# ============================================================================

def generate_chart(
    rows: List[Dict[str, Any]],
    chart_type: str,
    x_column: str,
    y_column: str,
    title: Optional[str] = None,
    theme: str = "default",
    color: Optional[str] = None,
    show_grid: bool = True,
    show_legend: bool = False,
    figure_size: tuple = (10, 6),
    font_size: int = 10,
) -> Dict[str, Any]:
    """Generate a chart from query results and return as PNG bytes.
    
    Args:
        rows: List of data dictionaries from query
        chart_type: Type of chart (bar, line, pie, scatter)
        x_column: Column name for X-axis
        y_column: Column name for Y-axis (numeric)
        title: Optional custom chart title
        theme: Theme name from CHART_THEMES (default, dark, professional, colorful)
        color: Override theme color with hex color code
        show_grid: Whether to show grid lines
        show_legend: Whether to show legend
        figure_size: Tuple of (width, height) in inches
        font_size: Base font size for labels
    """
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    
    if not rows:
        return {"success": False, "error": "No data to chart"}
    
    df = pd.DataFrame(rows)
    
    # Validate columns exist
    if x_column not in df.columns:
        return {"success": False, "error": f"Column '{x_column}' not found in data"}
    if y_column not in df.columns:
        return {"success": False, "error": f"Column '{y_column}' not found in data"}
    
    try:
        # Get theme settings
        if theme not in CHART_THEMES:
            theme = "default"
        theme_config = CHART_THEMES[theme]
        
        # Use override color or theme color
        chart_color = color or theme_config["color"]
        bg_color = theme_config["background_color"]
        use_grid = show_grid and theme_config["grid"]
        use_legend = show_legend or theme_config["legend"]
        title_size = theme_config.get("title_size", 14)
        
        fig, ax = plt.subplots(figsize=figure_size)
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        x_data = df[x_column]
        y_data = pd.to_numeric(df[y_column], errors="coerce")
        
        chart_title = title or f"{y_column} by {x_column}"
        
        if chart_type == "bar":
            ax.bar(x_data, y_data, color=chart_color)
            ax.set_xlabel(x_column, fontsize=font_size)
            ax.set_ylabel(y_column, fontsize=font_size)
        elif chart_type == "line":
            ax.plot(x_data, y_data, marker="o", color=chart_color, linewidth=2)
            ax.set_xlabel(x_column, fontsize=font_size)
            ax.set_ylabel(y_column, fontsize=font_size)
        elif chart_type == "pie":
            ax.pie(y_data, labels=x_data.tolist(), autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
        elif chart_type == "scatter":
            ax.scatter(x_data, y_data, color=chart_color, alpha=0.7, s=50)
            ax.set_xlabel(x_column, fontsize=font_size)
            ax.set_ylabel(y_column, fontsize=font_size)
        else:
            return {"success": False, "error": f"Unknown chart type: {chart_type}"}
        
        ax.set_title(chart_title, fontsize=title_size, fontweight="bold")
        
        # Grid styling
        if use_grid and chart_type != "pie":
            ax.grid(True, alpha=0.3, linestyle="--")
        
        # Legend
        if use_legend:
            ax.legend(loc="best", fontsize=font_size)
        
        # Rotate x labels for better readability
        if chart_type != "pie":
            plt.xticks(rotation=45, ha="right", fontsize=font_size)
            plt.yticks(fontsize=font_size)
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=bg_color)
        buf.seek(0)
        chart_data = buf.getvalue()
        plt.close(fig)
        
        filename = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        return {
            "success": True,
            "chart_data": chart_data,
            "file_name": filename,
            "mime": "image/png",
            "chart_type": chart_type,
            "title": chart_title,
            "theme": theme,
        }
    except Exception as e:
        plt.close("all")
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

CHART_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Create a visual chart from query results. Use when user asks to visualize, chart, graph, or plot data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter"],
                        "description": "Type of chart: bar for comparisons, line for trends, pie for proportions, scatter for correlations."
                    },
                    "x_column": {
                        "type": "string",
                        "description": "Column name for X-axis (categories/labels)."
                    },
                    "y_column": {
                        "type": "string",
                        "description": "Column name for Y-axis (numeric values)."
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional chart title."
                    }
                },
                "required": ["chart_type", "x_column", "y_column"]
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
    Process user query using LLM with tool calling for exports and charts.
    
    The LLM decides whether to:
    1. Generate SQL for data queries
    2. Call export_data tool for export requests
    3. Generate SQL AND export in one go
    4. Create charts from data
    5. Provide a direct answer
    """
    # Retrieve schema context
    docs = vector_store.as_retriever(k=4).invoke(query)
    schema_context = "\n\n".join(doc.page_content for doc in docs)
    
    # Build system prompt
    has_data = bool(last_results)
    
    # Get available columns from last results for chart generation
    available_columns = list(last_results[0].keys()) if has_data and last_results else []
    columns_info = f"Available columns in current data: {available_columns}" if available_columns else ""
    
    system_prompt = f"""You are an expert SQLite SQL generator and data assistant.

You MUST respond in valid JSON only. No markdown, no explanations outside JSON.

For data queries, respond with:
{{"type": "sql", "sql": "<SELECT QUERY>"}}

For data queries where the user ALSO wants to export/download the results (e.g., "give me categories as CSV", "show products and export as PDF"), respond with:
{{"type": "sql_and_export", "sql": "<SELECT QUERY>", "format": "csv" | "excel" | "pdf"}}

For data queries where the user wants to visualize/chart the results (e.g., "show me products as a bar chart", "graph sales by category"), respond with:
{{"type": "sql_and_chart", "sql": "<SELECT QUERY>", "chart_type": "bar" | "line" | "pie" | "scatter", "x_column": "<column>", "y_column": "<column>", "title": "<optional title>", "theme": "default" | "dark" | "professional" | "colorful"}}

{"For chart requests when you already have data:" if has_data else ""}
{'{{"type": "chart", "chart_type": "bar" | "line" | "pie" | "scatter", "x_column": "<column>", "y_column": "<column>", "title": "<optional title>", "theme": "default" | "dark" | "professional" | "colorful"}}' if has_data else ""}
{columns_info}

{"For export requests when you already have data, respond with:" if has_data else ""}
{'{{"type": "export", "format": "csv" | "excel" | "pdf"}}' if has_data else ""}

For questions or impossible queries, respond with:
{{"type": "message", "content": "<response>"}}

Rules:
- Use ONLY tables/columns from the provided schema
- SQL must be SELECT-only and SQLite compatible  
- Never invent tables or columns
- If user asks for data AND wants to download/export/save it, use "sql_and_export" type
- If user asks for data AND wants to visualize/chart/graph it, use "sql_and_chart" type
- For charts, x_column should be categorical (names, labels), y_column should be numeric
- Supported export formats: csv, excel, pdf
- Supported chart types: bar, line, pie, scatter"""

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
    
    # Handle chart request when we have data
    if resp_type == "chart" and has_data:
        result = generate_chart(
            last_results,
            parsed.get("chart_type", "bar"),
            parsed.get("x_column"),
            parsed.get("y_column"),
            parsed.get("title"),
            theme=parsed.get("theme", "default"),
        )
        if result["success"]:
            return {
                "type": "chart",
                "answer": f"Here's your {result['chart_type']} chart: {result['title']}",
                "chart_data": result["chart_data"],
                "file_name": result["file_name"],
                "mime": result["mime"],
                "theme": result.get("theme", "default"),
            }
        return {
            "type": "answer",
            "answer": f"Sorry, I couldn't generate the chart: {result['error']}",
        }
    
    # Handle SQL + chart combined request
    if resp_type == "sql_and_chart":
        return {
            "type": "sql_and_chart",
            "sql": parsed.get("sql"),
            "chart_type": parsed.get("chart_type", "bar"),
            "x_column": parsed.get("x_column"),
            "y_column": parsed.get("y_column"),
            "title": parsed.get("title"),
            "theme": parsed.get("theme", "default"),
            "content": docs,
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
