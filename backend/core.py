import json
from typing import Any, Dict, List
import os 
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# init embeddings 
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    show_progress_bar=False,
    chunk_size=50,
    retry_min_seconds=10
)

# init vector store
vector_store = PineconeVectorStore(
    index_name=os.getenv("INDEX_NAME"),
    embedding=embeddings,
)

# init chat model
chat_model = init_chat_model(
    model="gpt-5.2",model_provider="openai",
)

@tool(response_format="content_and_artifact")

def retrieve_context(query: str):
    """Retrieve relevant documents to help answer the queries about langchain."""
    # retrieve top-4k relevant documents
    retrieve_docs = vector_store.as_retriever().invoke(query,k=4)

    #serialize documents
    serialized = "\n\n".join(
        (f"Source: {doc.metadata.get('source', 'unknown')}\n\nContent: {doc.page_content}") for doc in retrieve_docs)
    
    # return both serialized documents and the original query
    return serialized,retrieve_docs

def run_llm(query: str) -> Dict[str, Any]:
    system_prompt = """
You are an expert SQLite SQL generator.

You MUST respond in valid JSON.
Do NOT include markdown.
Do NOT include explanations outside JSON.

If the user asks for data or a query, respond with:
{
  "type": "sql",
  "sql": "<SQLITE SELECT QUERY ONLY>"
}

If the user is asking a question or the query is not possible, respond with:
{
  "type": "message",
  "content": "<natural language response>"
}

Rules:
- Use ONLY tables and columns from the provided schema
- NEVER invent tables or columns
- SQL must be SELECT-only
- SQLite compatible
- If impossible, respond with type=message
"""

    # Retrieve schema context
    retrieved_docs = vector_store.as_retriever(k=4).invoke(query)

    schema_context = "\n\n".join(
        doc.page_content for doc in retrieved_docs
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""
Schema:
{schema_context}

User question:
{query}
"""
        }
    ]

    response = chat_model.invoke(messages)
    raw = response.content.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "type": "message",
            "content": raw
        }

    # Normalize the parsed model output into the shape expected by the UI
    # `main.py` expects top-level keys: `type`, `answer`, `sql`, and `content` (context docs).
    resp_type = parsed.get("type") if isinstance(parsed, dict) else None

    if resp_type == "message":
        return {
            "type": "answer",
            "answer": parsed.get("content", "") if isinstance(parsed, dict) else str(parsed),
            "sql": None,
            "content": retrieved_docs,
        }

    if resp_type == "sql":
        return {
            "type": "sql",
            "answer": parsed.get("content", "") if isinstance(parsed, dict) else "",
            "sql": parsed.get("sql") if isinstance(parsed, dict) else None,
            "content": retrieved_docs,
        }

    # Fallback: return the raw parsed payload mapped into expected keys
    return {
        "type": resp_type or "answer",
        "answer": parsed.get("content") if isinstance(parsed, dict) else str(parsed),
        "sql": parsed.get("sql") if isinstance(parsed, dict) else None,
        "content": retrieved_docs,
    }


def format_sql_results(original_query: str, sql: str, rows: List[Dict[str, Any]]) -> str:
    """
    Send SQL results back to the LLM to format and present nicely.
    Returns a formatted natural language response with the results.
    """

    if not rows:
        return "The query returned no results."

    # Convert any bytes in rows to strings for JSON serialization
    def sanitize(val):
        if isinstance(val, bytes):
            try:
                return val.decode('utf-8')
            except Exception:
                return val.hex()
        return val

    def sanitize_row(row):
        return {k: sanitize(v) for k, v in row.items()}

    safe_rows = [sanitize_row(row) for row in rows]
    rows_str = json.dumps(safe_rows, indent=2)

    system_prompt = """
You are a helpful data analysis assistant. The user asked a question, we executed SQL to get results, and now you need to present the results in a clear, user-friendly way.

Format the results nicely and explain what they show. Be conversational but concise.
Do NOT respond in JSON format. Just provide a natural language response explaining the data.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""
Original question: {original_query}

SQL executed: {sql}

Results returned ({len(rows)} rows):
{rows_str}

Please present these results in a clear, user-friendly way.
"""
        }
    ]

    response = chat_model.invoke(messages)
    return response.content.strip()



if __name__ == "__main__":
    result = run_llm("give me the SQL query to find all customers who have placed more than 5 orders in the last month.")
    print(result)