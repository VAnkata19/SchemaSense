import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from logger import (Colors, log_error, log_header, log_info, log_success,
                    log_warning)

load_dotenv()

import re

with open("nstnwnd.sql", "r", encoding="utf-8") as f:
    sql_text = f.read()

# Capture CREATE TABLE ... ); blocks (non-greedy)
table_blocks = re.findall(r"(CREATE\s+TABLE[\s\S]*?\)\s*GO)", sql_text, flags=re.IGNORECASE)

def _clean_identifier(name: str) -> str:
    return name.strip().strip('`"[]')

def sql_table_to_text(sql_block: str) -> dict:
    # extract the block header (up to first '(') to find table name
    table_name = "unknown"
    m_name = re.search(r"CREATE\s+TABLE\s+(.*?)\s*\(", sql_block, flags=re.IGNORECASE | re.DOTALL)
    if m_name:
        raw = m_name.group(1).strip()
        # if schema-qualified like dbo."Order Details", take last part
        if "." in raw:
            raw = raw.split(".")[-1]
        table_name = _clean_identifier(raw)

    # extract the inside of parentheses for columns and constraints
    columns = []
    m_cols = re.search(r"\(([\s\S]*?)\)\s*GO", sql_block, flags=re.IGNORECASE)
    inner = None
    if m_cols:
        inner = m_cols.group(1)
    else:
        # fallback: everything between first '(' and last ')'
        try:
            start = sql_block.index("(") + 1
            end = sql_block.rindex(")")
            inner = sql_block[start:end]
        except ValueError:
            inner = None

    relations = []
    if inner:
        for raw_line in inner.splitlines():
            l = raw_line.strip()
            if not l:
                continue
            # remove trailing commas
            l = l.rstrip(",").strip()
            # capture constraint/primary/foreign lines separately
            if re.match(r"^(PRIMARY|FOREIGN|CONSTRAINT|UNIQUE|CHECK)\b", l, flags=re.IGNORECASE):
                relations.append(l)
                continue
            # skip closing paren lines
            if l == ")":
                continue
            columns.append(l)

    doc_text = f"""
Table name: {table_name}

Description:
This table is part of the nstnwnd database schema.

Columns:
"""
    for col in columns:
        doc_text += f"- {col}\n"

    if relations:
        doc_text += "\nRelationships / Constraints:\n"
        for r in relations:
            doc_text += f"- {r}\n"

    return {
        "table": table_name,
        "text": doc_text.strip(),
        "columns": columns,
        "relations": relations,
    }


documents = []
# Simple chunking: 1 table = 1 chunk. If a table has many columns, split into columns vs relations.
for block in table_blocks:
    tbl_info = sql_table_to_text(block)
    table_name = tbl_info.get("table", "unknown")
    cols = tbl_info.get("columns", [])
    rels = tbl_info.get("relations", [])

    # if table is massive, split into two chunks
    if len(cols) > 80:
        # chunk 1: columns (first half)
        mid = len(cols) // 2
        cols_text = f"Table name: {table_name}\n\nColumns (part 1):\n"
        for c in cols[:mid]:
            cols_text += f"- {c}\n"
        documents.append({
            "text": cols_text.strip(),
            "metadata": {"source": "nstnwnd.sql", "type": "schema", "table": table_name, "chunk": 1},
        })

        cols_text2 = f"Table name: {table_name}\n\nColumns (part 2):\n"
        for c in cols[mid:]:
            cols_text2 += f"- {c}\n"
        # include relations in second chunk
        if rels:
            cols_text2 += "\nRelationships / Constraints:\n"
            for r in rels:
                cols_text2 += f"- {r}\n"
        documents.append({
            "text": cols_text2.strip(),
            "metadata": {"source": "nstnwnd.sql", "type": "schema", "table": table_name, "chunk": 2},
        })
    else:
        documents.append({
            "text": tbl_info.get("text", ""),
            "metadata": {"source": "nstnwnd.sql", "type": "schema", "table": table_name},
        })

log_success(f"Prepared {len(documents)} documents for embedding/storage")

# Initialize text splitter (in case we need to split further)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)
# Split documents if needed
final_docs: List[Document] = []
for doc in documents:
    splits = text_splitter.split_text(doc["text"])
    if len(splits) == 1:
        final_docs.append(Document(page_content=splits[0], metadata=doc["metadata"]))
    else:
        for i, chunk in enumerate(splits):
            metadata = doc["metadata"].copy()
            metadata["subchunk"] = i + 1
            final_docs.append(Document(page_content=chunk, metadata=metadata))

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