"""
Environment & Configuration Verification Script
------------------------------------------------
Tests that all installed libraries, virtual environment, and config.py
are functioning properly before proceeding to Phase 2.
"""

import sys
import sqlite3

def run_checks():
    print("=" * 60)
    print("JobInsight - Environment Verification Test")
    print("=" * 60)
    
    # Check Python version
    print(f"[OK] Python version: {sys.version.split()[0]}")
    print(f"[OK] Python executable: {sys.executable}")
    
    # Check dependencies
    try:
        import requests
        print(f"[OK] requests: {requests.__version__}")
    except ImportError as e:
        print(f"[FAIL] requests import error: {e}")
        return False

    try:
        import pandas as pd
        print(f"[OK] pandas: {pd.__version__}")
    except ImportError as e:
        print(f"[FAIL] pandas import error: {e}")
        return False

    try:
        import fastapi
        print(f"[OK] fastapi: {fastapi.__version__}")
    except ImportError as e:
        print(f"[FAIL] fastapi import error: {e}")
        return False

    try:
        import uvicorn
        print(f"[OK] uvicorn: {uvicorn.__version__}")
    except ImportError as e:
        print(f"[FAIL] uvicorn import error: {e}")
        return False

    try:
        import jinja2
        print(f"[OK] jinja2: {jinja2.__version__}")
    except ImportError as e:
        print(f"[FAIL] jinja2 import error: {e}")
        return False

    # Check built-in SQLite
    print(f"[OK] sqlite3 (built-in): SQLite library version {sqlite3.sqlite_version}")

    # Check config.py
    try:
        import config
        print(f"[OK] config.py loaded successfully")
        print(f"     - Base dir: {config.BASE_DIR}")
        print(f"     - Data dir: {config.DATA_DIR}")
        print(f"     - DB path:  {config.DATABASE_PATH}")
        print(f"     - API URL:  {config.HIMALAYAS_API_BASE_URL}")
        print(f"     - User-Agent: {config.DEFAULT_USER_AGENT}")
    except Exception as e:
        print(f"[FAIL] config.py error: {e}")
        return False

    print("=" * 60)
    print("SUCCESS: Phase 1 environment is fully verified and ready!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
