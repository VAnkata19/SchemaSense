"""Data export functionality."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)


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
