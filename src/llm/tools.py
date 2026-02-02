"""LLM tool definitions."""

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
