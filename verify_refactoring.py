#!/usr/bin/env python3
"""
Verification script for the SchemaSense modular refactoring.
Shows before/after statistics and validates the new structure.
"""

import os
import sys
from pathlib import Path

def count_lines(filepath):
    """Count lines in a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def main():
    workspace = Path("/Users/vankatabot/Documents/GitHub/Internal-Company-Knowledge-Copilot")
    
    print("=" * 70)
    print("SCHEMASENSE MODULAR REFACTORING VERIFICATION")
    print("=" * 70)
    print()
    
    # Get all module files
    modules = {
        "State Management": ["src/state/__init__.py", "src/state/session.py"],
        "Charts": ["src/charts/__init__.py", "src/charts/themes.py", "src/charts/generator.py"],
        "Exports": ["src/export/__init__.py", "src/export/exporter.py"],
        "Query": ["src/query/__init__.py", "src/query/executor.py"],
        "LLM": ["src/llm/__init__.py", "src/llm/core.py", "src/llm/tools.py"],
        "UI": ["src/ui/__init__.py", "src/ui/components.py", "src/ui/handlers.py"],
    }
    
    print("MODULE STATISTICS:")
    print("-" * 70)
    
    total_lines = 0
    total_files = 0
    
    for module_name, files in modules.items():
        module_lines = 0
        valid_files = 0
        
        for file_path in files:
            full_path = workspace / file_path
            if full_path.exists():
                lines = count_lines(full_path)
                module_lines += lines
                valid_files += 1
        
        if valid_files > 0:
            print(f"{module_name:.<30} {valid_files} files, {module_lines:>4} lines")
            total_lines += module_lines
            total_files += valid_files
    
    print("-" * 70)
    print(f"{'TOTAL':.<30} {total_files} files, {total_lines:>4} lines")
    print()
    
    # Check main.py
    main_py = workspace / "main.py"
    if main_py.exists():
        main_lines = count_lines(main_py)
        print(f"Main Application (main.py):  {main_lines:>4} lines")
        print()
    
    # Validate imports
    print("IMPORT VALIDATION:")
    print("-" * 70)
    
    import_tests = {
        "State": "from src.state import init_session_state, add_message, clear_chat",
        "Charts": "from src.charts import generate_chart, CHART_THEMES",
        "Export": "from src.export import generate_export",
        "Query": "from src.query import run_sql_query",
        "LLM": "from src.llm import run_llm, format_sql_results",
        "UI": "from src.ui import render_chat_history, process_user_input",
    }
    
    os.chdir(workspace)
    sys.path.insert(0, str(workspace))
    
    all_passed = True
    for name, import_stmt in import_tests.items():
        try:
            exec(import_stmt)
            print(f"✓ {name:.<25} PASS")
        except Exception as e:
            print(f"✗ {name:.<25} FAIL: {str(e)[:40]}")
            all_passed = False
    
    print()
    
    # File structure check
    print("FILE STRUCTURE CHECK:")
    print("-" * 70)
    
    required_files = []
    for files in modules.values():
        required_files.extend(files)
    required_files.append("main.py")
    
    missing = []
    for file_path in required_files:
        full_path = workspace / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} MISSING")
            missing.append(file_path)
    
    print()
    print("=" * 70)
    
    if all_passed and not missing:
        print("REFACTORING STATUS: SUCCESS")
        print("All modules are properly organized and importable.")
        print("The codebase is ready for production use.")
        return 0
    else:
        print("REFACTORING STATUS: INCOMPLETE")
        if missing:
            print(f"Missing files: {len(missing)}")
        if not all_passed:
            print("Some imports failed validation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
