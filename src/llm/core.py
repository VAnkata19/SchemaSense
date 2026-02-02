"""LLM core functionality."""

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

from src.export import generate_export
from src.charts import generate_chart, CHART_THEMES
from .tools import EXPORT_TOOLS, CHART_TOOLS

load_dotenv()

# Initialize embeddings and vector store
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

# Initialize chat model
chat_model = init_chat_model(
    model="gpt-5.2",
    model_provider="openai",
)


def _get_llm_response(content: Any) -> str:
    """Extract string content from LLM response."""
    if isinstance(content, list):
        return str(content[0]) if content else ""
    return str(content)


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
