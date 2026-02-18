# SchemaSense - Internal Company Knowledge Copilot

Stop writing SQL. Start asking questions. SchemaSense turns your company's database into a conversational knowledge base — letting anyone on your team extract insights, generate reports, and visualize data just by typing what they want to know.

## Overview

SchemaSense is a Streamlit-based application that bridges the gap between business users and databases. It leverages OpenAI's language models to convert natural language questions into SQL queries, execute them, and provide insights through interactive chat, data exports, and visualizations.

## Short Demo

https://github.com/user-attachments/assets/cf461532-01a2-491a-af26-1ea619c141af

## Features

- **Natural Language Querying**: Ask questions about your data in plain English
- **Intelligent SQL Generation**: LLM-powered SQL query generation with human approval workflow
- **Data Visualization**: Automatic chart generation from query results
- **Data Export**: Export results to CSV and PDF formats
- **Chat Interface**: Conversational interaction with chat history
- **Vector Search**: Semantic search capabilities using Pinecone vector database
- **Data Ingestion**: Automated pipeline for ingesting company data

## Architecture

```
SchemaSense/
├── main.py                 # Streamlit application entry point
├── backend/               # Backend services
│   ├── core.py           # LLM initialization and tool management
│   └── run_sql_query.py  # SQL query execution
├── src/                  # Source modules
│   ├── llm/             # Language model interface
│   ├── query/           # Query execution logic
│   ├── charts/          # Chart generation
│   ├── export/          # Data export functionality
│   ├── ui/              # UI components and handlers
│   └── state/           # Session state management
├── ingestion/           # Data ingestion pipeline
├── pages/               # Streamlit pages
└── data/                # SQL schema and data files
```

## Installation

### Requirements
- Python 3.13+
- OpenAI API key
- Pinecone API key and index

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Internal-Company-Knowledge-Copilot
```

2. Install dependencies:
```bash
pip install -e .
```

3. Configure environment variables:
Create a `.env` file in the project root:
```
OPENAI_API_KEY=<your-openai-api-key>
PINECONE_API_KEY=<your-pinecone-api-key>
INDEX_NAME=<your-pinecone-index-name>
```

4. Run the application:
```bash
streamlit run main.py
```

## Usage

### Querying Data

1. Start the application - it will open in your browser at `http://localhost:8501`
2. Type a natural language question in the chat input (e.g., "Show me sales by region")
3. Review the generated SQL query
4. Approve or reject the query
5. View results and interact with the response

### Data Export

Click the export button in chat to save results as:
- CSV format for spreadsheet analysis
- PDF format for reports

### Visualizations

Generate charts automatically from query results with customizable themes.

## Key Components

### LLM Core (`src/llm/`)
- Language model initialization and management
- Tool calling for exports and charts
- Query context retrieval from vector store

### Query Execution (`src/query/`)
- SQL execution engine
- Query validation and sanitization
- Result processing

### UI Components (`src/ui/`)
- Chat history rendering
- SQL approval workflow
- User input processing
- Chat interface handlers

### Charts (`src/charts/`)
- Chart generation from query results
- Multiple chart themes
- Matplotlib-based visualizations

### Export (`src/export/`)
- CSV export functionality
- PDF report generation
- Data formatting

### Data Ingestion (`ingestion/`)
- Vector embedding generation
- Pinecone index population
- Schema documentation ingestion

## Configuration

### LLM Model
The application uses OpenAI's GPT-5.2 model for query generation and chat interactions.

### Vector Store
Pinecone is used for semantic search and retrieval-augmented generation (RAG).

### Chat Settings
Clear chat history using the sidebar button to start a new conversation.

## Dependencies

Key dependencies include:
- **streamlit**: Web framework for the UI
- **langchain**: LLM orchestration and tool integration
- **langchain-openai**: OpenAI API integration
- **langchain-pinecone**: Vector store integration
- **pandas**: Data manipulation
- **matplotlib**: Chart generation
- **reportlab**: PDF generation

See `pyproject.toml` for the complete dependency list.

## Development

### Project Structure

- **Backend**: Core LLM and query execution logic
- **Frontend**: Streamlit UI with custom components
- **Ingestion**: Data pipeline for preparing company knowledge
- **State Management**: Session-based state for chat context

### Session State

The application maintains session state for:
- Chat history
- Pending SQL queries
- User settings
- Export preferences

## Workflow

1. **User Input**: Natural language question
2. **Vector Search**: Retrieve relevant schema information from Pinecone
3. **SQL Generation**: LLM generates SQL query with retrieved context
4. **User Approval**: User reviews and approves the generated SQL
5. **Query Execution**: Execute approved query against database
6. **Response Generation**: LLM generates natural language response with results
7. **Visualization**: Generate charts/exports based on user preferences

## Best Practices

- Review generated SQL queries before execution
- Use specific table and column names in questions
- Ask one question at a time for better results
- Export important results for archival

## Troubleshooting

### Connection Issues
- Verify OpenAI API key is valid
- Check Pinecone index is accessible
- Ensure database connection is configured

### Query Generation Issues
- Use more specific column names
- Reference table names explicitly
- Provide context about data relationships

## Contributing

When adding new features:
1. Follow the modular structure
2. Add docstrings to new functions
3. Update this README with new components
4. Test with sample queries

## Contact

For questions or issues, please contact the development team.
