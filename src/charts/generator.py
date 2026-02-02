"""Chart generation functionality."""

import io
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd
from .themes import CHART_THEMES


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
