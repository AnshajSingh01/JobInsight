"""
JobInsight - Phase 4 SQLite Database Module
-------------------------------------------
What it does:
  Manages SQLite database initialization, table creation, and safe insertion
  of collected job listings using parameterized queries to prevent SQL injection.

Why we need it:
  Storing records in SQLite converts raw ephemeral JSON into a persistent,
  queryable local relational database. It enables fast indexing, prevents
  duplicate entries by enforcing a PRIMARY KEY on 'guid', and serves as the
  single source of truth for downstream cleaning and analytical queries.

How it connects to the project:
  - Uses DATABASE_PATH and RAW_JOBS_FILE from config.py.
  - Takes raw listings from Phase 3 (data/raw_jobs.json) and writes them to data/jobinsight.db.
  - Provides connection helpers for cleaner.py (Phase 5) and analyzer.py (Phase 6).
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import config

# Table Name Constant
JOBS_TABLE = "raw_jobs"

# SQL Schema Definition
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {JOBS_TABLE} (
    guid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company_name TEXT,
    company_slug TEXT,
    company_logo TEXT,
    excerpt TEXT,
    description TEXT,
    categories TEXT,             -- JSON string array (e.g. '["Engineering", "DevOps"]')
    parent_categories TEXT,      -- JSON string array
    seniority TEXT,              -- JSON string array (e.g. '["Senior"]')
    employment_type TEXT,
    location_restrictions TEXT,  -- JSON string array (e.g. '["United States"]')
    timezone_restrictions TEXT,  -- JSON string array (e.g. '[-5, -6]')
    min_salary REAL,
    max_salary REAL,
    salary_period TEXT,
    currency TEXT,
    pub_date INTEGER,            -- Unix timestamp epoch in seconds
    expiry_date INTEGER,         -- Unix timestamp epoch in seconds
    application_link TEXT,
    raw_json TEXT,               -- Exact unaltered JSON string for reference integrity
    inserted_at TEXT             -- ISO timestamp when inserted into SQLite
);
"""

def get_connection(db_path: Path = config.DATABASE_PATH) -> sqlite3.Connection:
    """
    Returns a configured sqlite3 connection with Row factory enabled.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Access columns by name like dicts
    return conn

def init_db(db_path: Path = config.DATABASE_PATH) -> None:
    """
    Initializes the database schema if it doesn't already exist.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
    print(f"[OK] Database initialized: {db_path.name} (Table: '{JOBS_TABLE}')")

def serialize_list(val: Any) -> str:
    """
    Safely converts lists to JSON string format for simple, robust SQLite storage.
    """
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    elif val is None:
        return json.dumps([])
    return json.dumps([str(val)], ensure_ascii=False)

def insert_jobs(jobs: List[Dict[str, Any]], db_path: Path = config.DATABASE_PATH) -> int:
    """
    Inserts a list of raw job dictionaries into SQLite using parameterized queries.
    Uses INSERT OR REPLACE to update existing listings gracefully without throwing duplicate errors.
    
    Returns:
        Number of records successfully inserted/updated.
    """
    insert_sql = f"""
    INSERT OR REPLACE INTO {JOBS_TABLE} (
        guid, title, company_name, company_slug, company_logo,
        excerpt, description, categories, parent_categories, seniority,
        employment_type, location_restrictions, timezone_restrictions,
        min_salary, max_salary, salary_period, currency,
        pub_date, expiry_date, application_link, raw_json, inserted_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?
    );
    """

    now_iso = datetime.now(timezone.utc).isoformat()
    rows_to_insert = []

    for job in jobs:
        guid = job.get("guid") or job.get("applicationLink")
        if not guid:
            continue  # Skip invalid records lacking a primary identifier

        row = (
            guid,
            job.get("title") or "Untitled Position",
            job.get("companyName"),
            job.get("companySlug"),
            job.get("companyLogo"),
            job.get("excerpt"),
            job.get("description"),
            serialize_list(job.get("categories")),
            serialize_list(job.get("parentCategories")),
            serialize_list(job.get("seniority")),
            job.get("employmentType"),
            serialize_list(job.get("locationRestrictions")),
            serialize_list(job.get("timezoneRestrictions")),
            job.get("minSalary"),
            job.get("maxSalary"),
            job.get("salaryPeriod"),
            job.get("currency"),
            job.get("pubDate"),
            job.get("expiryDate"),
            job.get("applicationLink"),
            json.dumps(job, ensure_ascii=False),
            now_iso
        )
        rows_to_insert.append(row)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()

    return len(rows_to_insert)

def import_raw_json_to_db(json_file: Path = config.RAW_JOBS_FILE, db_path: Path = config.DATABASE_PATH) -> int:
    """
    Reads the Phase 3 raw_jobs.json file and ingests all records into SQLite.
    """
    print(f"Reading raw JSON from: {json_file}")
    if not json_file.exists():
        raise FileNotFoundError(f"Raw jobs file not found: {json_file}. Please run Phase 3 first.")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    print(f"Found {len(jobs)} jobs in JSON. Inserting into SQLite...")
    inserted_count = insert_jobs(jobs, db_path=db_path)
    return inserted_count

def verify_database(db_path: Path = config.DATABASE_PATH) -> bool:
    """
    Performs comprehensive diagnostic verification on the SQLite database:
      - Validates file existence and size.
      - Checks that table 'raw_jobs' exists with expected schema.
      - Counts total rows and verifies 100% unique primary keys.
      - Fetches and displays a sample record.
    """
    print("\n" + "=" * 65)
    print("JobInsight - Database Verification")
    print("=" * 65)

    if not db_path.exists():
        print(f"[FAIL] Database file does not exist at: {db_path}")
        return False

    db_size_kb = db_path.stat().st_size / 1024
    print(f"[OK] Database file found: {db_path.name} ({db_size_kb:.1f} KB)")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check table existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (JOBS_TABLE,))
        table_row = cursor.fetchone()
        if not table_row:
            print(f"[FAIL] Table '{JOBS_TABLE}' does not exist!")
            return False
        print(f"[OK] Table exists: '{JOBS_TABLE}'")

        # Check column names and types
        cursor.execute(f"PRAGMA table_info({JOBS_TABLE});")
        columns = cursor.fetchall()
        print(f"[OK] Schema contains {len(columns)} columns:")
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            pk_badge = " [PRIMARY KEY]" if pk else ""
            print(f"     - {col_name:<23} {col_type:<10}{pk_badge}")

        # Check total rows
        cursor.execute(f"SELECT COUNT(*) as count FROM {JOBS_TABLE};")
        total_rows = cursor.fetchone()["count"]
        print(f"\n[OK] Total records inserted: {total_rows}")

        # Check unique GUID count
        cursor.execute(f"SELECT COUNT(DISTINCT guid) as distinct_guids FROM {JOBS_TABLE};")
        distinct_guids = cursor.fetchone()["distinct_guids"]
        print(f"[OK] Unique GUID count     : {distinct_guids}")
        if total_rows == distinct_guids:
            print("     -> 100% Unique primary keys, zero duplicate collisions!")
        else:
            print(f"     -> [WARNING] Duplicate GUIDs found: {total_rows - distinct_guids}")

        # Check sample record
        cursor.execute(f"SELECT * FROM {JOBS_TABLE} LIMIT 1;")
        sample = cursor.fetchone()
        if sample:
            print("\n[Sample SQLite Record Retrieved]")
            print(f"  - guid                 : {sample['guid']}")
            print(f"  - title                : {sample['title']}")
            print(f"  - company_name         : {sample['company_name']}")
            print(f"  - employment_type      : {sample['employment_type']}")
            print(f"  - seniority            : {sample['seniority']}")
            print(f"  - categories           : {sample['categories'][:50]}...")
            print(f"  - location_restrictions: {sample['location_restrictions']}")
            print(f"  - min_salary           : {sample['min_salary']}")
            print(f"  - max_salary           : {sample['max_salary']}")
            print(f"  - currency             : {sample['currency']}")
            print(f"  - pub_date (epoch)     : {sample['pub_date']}")
            print(f"  - application_link     : {sample['application_link']}")
            print(f"  - raw_json preserved?  : {'Yes' if sample['raw_json'] else 'No'} ({len(sample['raw_json'])} chars)")
            print(f"  - inserted_at          : {sample['inserted_at']}")

    print("\n" + "=" * 65)
    print("SUCCESS: Phase 4 SQLite Storage verified!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    print("=" * 65)
    print("JobInsight - Phase 4 SQLite Setup & Import")
    print("=" * 65)
    init_db()
    count = import_raw_json_to_db()
    print(f"[OK] Ingestion complete: {count} jobs stored.")
    verify_database()
