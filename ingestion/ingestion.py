import os
import sqlite3
from typing import Any, Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from logger import (Colors, log_error, log_header, log_info, log_success,
                    log_warning)

load_dotenv()

import re

# Use absolute path or find the file
sql_file_paths = [
    "nstnwnd.sql",
    "/Users/vankatabot/Documents/GitHub/Internal-Company-Knowledge-Copilot/nstnwnd.sql",
    "./nstnwnd.sql",
]

sql_text = None
for path in sql_file_paths:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            sql_text = f.read()
        break

if sql_text is None:
    raise FileNotFoundError("Could not find nstnwnd.sql in any expected location")

# Capture CREATE TABLE ... blocks - look for next CREATE or INSERT or end of CREATE statement
table_blocks = re.findall(r"(CREATE\s+TABLE\s+[\[\`\"]?\w+[\]\`\"]?[\s\S]*?)(?=\n(?:CREATE|INSERT|DROP|PRAGMA|$))", sql_text, flags=re.IGNORECASE)

log_success(f"Found {len(table_blocks)} table definitions")

def _clean_identifier(name: str) -> str:
    return name.strip().strip('`"[]')

def sql_table_to_text(sql_block: str) -> dict:
    """Extract table name and return the CREATE TABLE statement."""
    # extract the block header (up to first '(') to find table name
    table_name = "unknown"
    m_name = re.search(r"CREATE\s+TABLE\s+(.*?)\s*\(", sql_block, flags=re.IGNORECASE | re.DOTALL)
    if m_name:
        raw = m_name.group(1).strip()
        # if schema-qualified like dbo."Order Details", take last part
        if "." in raw:
            raw = raw.split(".")[-1]
        table_name = _clean_identifier(raw)

    # Clean up the CREATE TABLE statement for better readability
    doc_text = sql_block.strip()
    
    return {
        "table": table_name,
        "text": doc_text,
    }


# Create documents: one per CREATE TABLE statement
documents = []
for block in table_blocks:
    tbl_info = sql_table_to_text(block)
    table_name = tbl_info.get("table", "unknown")

    # Use the full CREATE TABLE statement as-is
    documents.append({
        "text": tbl_info.get("text", ""),
        "metadata": {
            "source": "nstnwnd.sql",
            "type": "table_schema",
            "table": table_name,
        },
    })

log_success(f"Prepared {len(documents)} CREATE TABLE documents for embedding")
log_info(f"  - Tables: {len(documents)}")

# Convert documents to Langchain Document objects without splitting
# Keep each CREATE TABLE as a single document
final_docs: List[Document] = []
for doc in documents:
    final_docs.append(Document(page_content=doc["text"], metadata=doc["metadata"]))

log_success(f"Final document count after splitting: {len(final_docs)}")

# Initialize embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    show_progress_bar=False,
    chunk_size=50,
    retry_min_seconds=10
)

# Initialize Pinecone vector store
vector_store = PineconeVectorStore(
    index_name=os.getenv("INDEX_NAME"),
    embedding=embeddings,
)
# Store documents in vector store
vector_store.add_documents(final_docs)
log_success("Ingestion complete: SQL schema documents have been embedded and stored.")

# Create SQLite database from SQL file
db_path = Path(__file__).parent.parent / "northwind.db"
try:
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Extract only CREATE TABLE statements (ignore INSERT, DROP, etc.)
    create_statements = re.findall(
        r"CREATE\s+TABLE\s+[\[\`\"]?\w+[\]\`\"]?[\s\S]*?;",
        sql_text,
        flags=re.IGNORECASE
    )
    
    # Execute each CREATE TABLE statement
    for statement in create_statements:
        try:
            cursor.execute(statement)
        except sqlite3.Error as e:
            log_warning(f"SQL Error executing statement: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    log_success(f"Database created successfully: {db_path}")
    log_info(f"  - Tables created: {len(create_statements)}")
    
except Exception as e:
    log_error(f"Failed to create database: {e}")
    raise