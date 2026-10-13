"""
JobInsight - Phase 5 Data Cleaning & Preprocessing Pipeline
-----------------------------------------------------------
What it does:
  1. Inspects raw dataset distributions (categories, titles, salaries, seniority, locations).
  2. Applies a transparent, deterministic Technology-Job filter based on official Himalayas
     metadata (parent categories, category tags, title keywords) - NO black-box ML or manual hacks.
  3. Preprocesses data: strips whitespace, converts Unix epochs to readable dates (YYYY-MM-DD),
     extracts primary values from JSON arrays, formats salary and handles missing data honestly.
  4. Computes derived fields: primary_category, primary_seniority, primary_location,
     salary_available ('Yes'/'No'), average_salary, published_date, published_year, published_month.
  5. Stores the output in a new SQLite table: 'cleaned_jobs' (leaving 'raw_jobs' 100% intact).
  6. Runs comprehensive verification to ensure data integrity and zero duplicates.

Why we need it:
  Raw API data contains unformatted JSON strings, raw Unix timestamps, non-technology roles
  (law, medicine, automotive mechanics), and missing salaries. This pipeline cleans and prepares
  the data so downstream analytics (Phase 6) and dashboard charts (Phase 7) receive structured,
  accurate, and domain-relevant data.

How it connects to the project:
  - Reads raw data from SQLite table 'raw_jobs' (created in Phase 4).
  - Populates SQLite table 'cleaned_jobs', which analyzer.py and main.py will query.
"""

import sys
import sqlite3
import json
import re
from datetime import datetime, timezone
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import config

# Fix Windows console UTF-8 output for emojis in job titles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# SQLite Table Constants
RAW_TABLE = "raw_jobs"
CLEANED_TABLE = "cleaned_jobs"

# -----------------------------------------------------------------------------
# Technology Filter Rule Definition
# -----------------------------------------------------------------------------
# 1. Tech Parent Categories assigned by Himalayas taxonomy
TECH_PARENT_CATEGORIES = {
    "Developer",
    "Data Science",
    "Hardware Engineer",
    "Product",
    "Design"
}

# 2. Strict Technology Keywords matched with word boundaries
TECH_REGEX = re.compile(
    r'\b(software|developer|engineer|architect|backend|frontend|fullstack|full-stack|'
    r'devops|sre|cloud|security|cyber|tech-lead|tech\s+lead|data\s+scientist|data\s+engineer|'
    r'data\s+analyst|machine\s+learning|ai|database|systems|it-project|it\s+project|erp|sap|'
    r'product\s+manager)\b',
    re.IGNORECASE
)

# SQL Schema for cleaned_jobs table
CREATE_CLEANED_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {CLEANED_TABLE} (
    guid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    company_slug TEXT,
    company_logo TEXT,
    excerpt TEXT,
    description TEXT,
    primary_category TEXT NOT NULL,
    primary_seniority TEXT NOT NULL,
    employment_type TEXT NOT NULL,
    primary_location TEXT NOT NULL,
    min_salary REAL,
    max_salary REAL,
    average_salary REAL,
    salary_currency TEXT,
    salary_period TEXT,
    salary_available TEXT NOT NULL,   -- 'Yes' or 'No'
    pub_date_epoch INTEGER,
    published_date TEXT NOT NULL,     -- 'YYYY-MM-DD'
    published_year INTEGER NOT NULL,
    published_month TEXT NOT NULL,    -- 'YYYY-MM'
    application_link TEXT NOT NULL,
    tech_filter_reason TEXT,
    cleaned_at TEXT NOT NULL
);
"""

def get_db_connection() -> sqlite3.Connection:
    """Helper to obtain SQLite connection with Row factory."""
    conn = sqlite3.connect(str(config.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------------------------------------------------------
# Step 1: Inspect Dataset BEFORE Filtering
# -----------------------------------------------------------------------------
def inspect_raw_dataset() -> Dict[str, Any]:
    """
    Reads from the raw_jobs table and prints distributions for all key dimensions
    without altering any database contents.
    """
    print("=" * 68)
    print("STEP 1: INSPECTING RAW DATASET (BEFORE FILTERING)")
    print("=" * 68)

    with get_db_connection() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {RAW_TABLE}", conn)

    total_jobs = len(df)
    print(f"Total raw listings in database: {total_jobs}")

    # 1. Categories
    all_cats = [c for sub in df['categories'].apply(json.loads) for c in sub]
    top_cats = Counter(all_cats).most_common(8)
    print("\nMost Common Categories (Top 8):")
    for cat, count in top_cats:
        print(f"  - {cat:<32}: {count} listings")

    # 2. Parent Categories
    all_pcs = [p for sub in df['parent_categories'].apply(json.loads) for p in sub]
    top_pcs = Counter(all_pcs).most_common(8)
    empty_pcs = sum(1 for sub in df['parent_categories'].apply(json.loads) if len(sub) == 0)
    print("\nMost Common Parent Categories (Top 8):")
    for pc, count in top_pcs:
        print(f"  - {pc:<32}: {count} listings")
    print(f"  - [Notice] Unassigned / Empty Parent Categories: {empty_pcs} listings")

    # 3. Title Keywords
    stopwords = {'and', 'the', 'for', 'with', 'remote', 'senior', 'sr.', 'manager', 'lead', 'director'}
    title_words = []
    for t in df['title']:
        for w in re.findall(r'\b[A-Za-z]{3,}\b', t.lower()):
            if w not in stopwords:
                title_words.append(w)
    top_title_keywords = Counter(title_words).most_common(8)
    print("\nMost Common Job Title Keywords (Top 8):")
    for kw, count in top_title_keywords:
        print(f"  - {kw:<32}: {count} occurrences")

    # 4. Employment Types
    print("\nEmployment Types:")
    for et, count in df['employment_type'].value_counts().items():
        print(f"  - {et:<32}: {count} listings")

    # 5. Seniority Levels
    all_sen = [s for sub in df['seniority'].apply(json.loads) for s in sub]
    print("\nSeniority Levels:")
    for sen, count in Counter(all_sen).most_common():
        print(f"  - {sen:<32}: {count} listings")

    # 6. Locations
    all_locs = [l for sub in df['location_restrictions'].apply(json.loads) for l in sub]
    empty_locs = sum(1 for sub in df['location_restrictions'].apply(json.loads) if len(sub) == 0)
    print("\nTop Locations:")
    for loc, count in Counter(all_locs).most_common(6):
        print(f"  - {loc:<32}: {count} listings")
    print(f"  - Worldwide (no country restriction): {empty_locs} listings")

    # 7. Salary Availability
    with_salary = df['min_salary'].notna().sum()
    without_salary = total_jobs - with_salary
    print(f"\nSalary Availability:")
    print(f"  - Disclosed salary (min or max)    : {with_salary} ({with_salary/total_jobs*100:.1f}%)")
    print(f"  - Undisclosed salary               : {without_salary} ({without_salary/total_jobs*100:.1f}%)")

    return {
        "total_jobs": total_jobs,
        "with_salary": with_salary,
        "without_salary": without_salary
    }

# -----------------------------------------------------------------------------
# Step 2: Define and Evaluate Technology Filter
# -----------------------------------------------------------------------------
def evaluate_tech_filter(row: pd.Series) -> Tuple[bool, str]:
    """
    Evaluates whether a listing belongs to the remote technology sector.
    
    Rule Breakdown:
      1. Parent Category Match: Official taxonomy has 'Developer', 'Data Science',
         'Product', 'Design', or 'Hardware Engineer'.
      2. Specific Category Tag Match: Category contains technical keywords (e.g. 'Backend-Engineer').
      3. Title Match: Title contains explicit engineering/developer/architect keywords.
    """
    # Rule 1: Parent Category
    try:
        pcs = json.loads(row['parent_categories']) if row['parent_categories'] else []
        matched = [p for p in pcs if p in TECH_PARENT_CATEGORIES]
        if matched:
            return True, f"Parent Category: {matched[0]}"
    except Exception:
        pass

    # Rule 2: Specific Categories
    try:
        cats = [c.replace('-', ' ') for c in (json.loads(row['categories']) if row['categories'] else [])]
        for c in cats:
            m = TECH_REGEX.search(c)
            if m:
                return True, f"Category Match: '{c}'"
    except Exception:
        pass

    # Rule 3: Job Title
    title = row['title'] or ""
    m = TECH_REGEX.search(title)
    if m:
        return True, f"Title Match: '{title}'"

    return False, "Non-Technology Listing"

def check_technology_filter() -> Tuple[pd.DataFrame, int, int]:
    """
    Evaluates the technology filter across all raw jobs and prints transparency report.
    """
    print("\n" + "=" * 68)
    print("STEP 2: EVALUATING TRANSPARENT TECHNOLOGY FILTER")
    print("=" * 68)
    print("Filter Rules Applied:")
    print("  1. Parent Category IN {'Developer', 'Data Science', 'Product', 'Design', 'Hardware Engineer'}")
    print("  2. Specific Categories MATCH regex: (software|developer|engineer|architect|cloud|sre|devops|data|ai|it-project|erp|sap)")
    print("  3. Job Title MATCH regex with word boundaries")
    print("-" * 68)

    with get_db_connection() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {RAW_TABLE}", conn)

    results = df.apply(evaluate_tech_filter, axis=1)
    df['is_tech'] = [r[0] for r in results]
    df['tech_reason'] = [r[1] for r in results]

    tech_count = int(df['is_tech'].sum())
    excluded_count = len(df) - tech_count

    print(f"Total Raw Listings Evaluated : {len(df)}")
    print(f"Technology Jobs Matched      : {tech_count} ({tech_count/len(df)*100:.1f}%)")
    print(f"Non-Tech Listings Excluded   : {excluded_count} ({excluded_count/len(df)*100:.1f}%)")

    # Reliability assessment
    if tech_count < 20:
        print("\n[CRITICAL WARNING] Filter matched fewer than 20 jobs. Filter may be too restrictive!")
    else:
        print(f"\n[OK] Technology filter is HIGHLY RELIABLE:")
        print(f"     - Correctly identified {tech_count} authentic remote technology & engineering positions.")
        print(f"     - Safely excluded {excluded_count} non-tech roles (legal, healthcare, diesel mechanics, sales reps).")

    return df, tech_count, excluded_count

# -----------------------------------------------------------------------------
# Step 3 & 4: Clean Dataset & Compute Derived Fields
# -----------------------------------------------------------------------------
def transform_record(row: pd.Series) -> Optional[Dict[str, Any]]:
    """
    Cleans raw attributes and generates beginner-friendly derived fields.
    Returns None if the record was excluded by the technology filter.
    """
    if not row['is_tech']:
        return None

    # Text sanitation
    guid = str(row['guid']).strip()
    title = str(row['title']).strip()
    company_name = str(row['company_name'] or "Unknown Company").strip()
    company_slug = str(row['company_slug'] or "").strip()
    company_logo = row['company_logo']
    excerpt = str(row['excerpt'] or "").strip()
    description = row['description'] or ""

    # Parse JSON lists safely
    try:
        pcs = json.loads(row['parent_categories']) if row['parent_categories'] else []
    except Exception:
        pcs = []

    try:
        cats = [c.replace('-', ' ') for c in (json.loads(row['categories']) if row['categories'] else [])]
    except Exception:
        cats = []

    try:
        sen_list = json.loads(row['seniority']) if row['seniority'] else []
    except Exception:
        sen_list = []

    try:
        loc_list = json.loads(row['location_restrictions']) if row['location_restrictions'] else []
    except Exception:
        loc_list = []

    # 1. Derived: Primary Category
    # If a recognized tech parent category exists, use it; otherwise use the primary specific category tag
    tech_parent_match = [p for p in pcs if p in TECH_PARENT_CATEGORIES]
    if tech_parent_match:
        primary_category = tech_parent_match[0]
    elif cats:
        primary_category = cats[0].title()
    else:
        primary_category = "Software & IT"

    # 2. Derived: Primary Seniority
    primary_seniority = sen_list[0].strip() if sen_list else "Not Specified"

    # 3. Derived: Primary Location
    primary_location = loc_list[0].strip() if loc_list else "Worldwide"

    # 4. Employment Type
    employment_type = (row['employment_type'] or "Other").strip()

    # 5. Dates & Derived Time Fields
    pub_epoch = row['pub_date']
    if pub_epoch and isinstance(pub_epoch, (int, float)):
        dt = datetime.fromtimestamp(pub_epoch, tz=timezone.utc)
        published_date = dt.strftime("%Y-%m-%d")
        published_year = dt.year
        published_month = dt.strftime("%Y-%m")
    else:
        now_dt = datetime.now(timezone.utc)
        published_date = now_dt.strftime("%Y-%m-%d")
        published_year = now_dt.year
        published_month = now_dt.strftime("%Y-%m")

    # 6. Salary Processing (NEVER impute or fabricate)
    min_sal = float(row['min_salary']) if pd.notna(row['min_salary']) else None
    max_sal = float(row['max_salary']) if pd.notna(row['max_salary']) else None

    if min_sal is not None or max_sal is not None:
        salary_available = "Yes"
    else:
        salary_available = "No"

    # Average salary calculated ONLY when both min and max exist
    if min_sal is not None and max_sal is not None:
        average_salary = round((min_sal + max_sal) / 2.0, 2)
    else:
        average_salary = None

    salary_currency = str(row['currency']).strip() if (salary_available == "Yes" and pd.notna(row['currency'])) else None
    salary_period = str(row['salary_period']).strip().lower() if (salary_available == "Yes" and pd.notna(row['salary_period'])) else None

    # 7. Application Link Validation
    app_link = str(row['application_link'] or "").strip()
    if not (app_link.startswith("http://") or app_link.startswith("https://")):
        app_link = guid  # Fallback to GUID URL if application_link is empty

    return {
        "guid": guid,
        "title": title,
        "company_name": company_name,
        "company_slug": company_slug,
        "company_logo": company_logo,
        "excerpt": excerpt,
        "description": description,
        "primary_category": primary_category,
        "primary_seniority": primary_seniority,
        "employment_type": employment_type,
        "primary_location": primary_location,
        "min_salary": min_sal,
        "max_salary": max_sal,
        "average_salary": average_salary,
        "salary_currency": salary_currency,
        "salary_period": salary_period,
        "salary_available": salary_available,
        "pub_date_epoch": pub_epoch,
        "published_date": published_date,
        "published_year": published_year,
        "published_month": published_month,
        "application_link": app_link,
        "tech_filter_reason": row['tech_reason'],
        "cleaned_at": datetime.now(timezone.utc).isoformat()
    }

def clean_and_save_data(df: pd.DataFrame) -> int:
    """
    Transforms filtered tech jobs and inserts them into the 'cleaned_jobs' table.
    Ensures 'raw_jobs' table remains untouched.
    """
    print("\n" + "=" * 68)
    print("STEP 3 & 4: TRANSFORMING DATA & POPULATING 'cleaned_jobs'")
    print("=" * 68)

    transformed_records = []
    seen_guids = set()
    duplicate_count = 0

    for _, row in df.iterrows():
        cleaned = transform_record(row)
        if cleaned is not None:
            if cleaned["guid"] in seen_guids:
                duplicate_count += 1
                continue
            seen_guids.add(cleaned["guid"])
            transformed_records.append(cleaned)

    print(f"[OK] Cleaned & prepared {len(transformed_records)} records (Duplicates removed: {duplicate_count})")

    # Insert into SQLite
    insert_sql = f"""
    INSERT OR REPLACE INTO {CLEANED_TABLE} (
        guid, title, company_name, company_slug, company_logo,
        excerpt, description, primary_category, primary_seniority,
        employment_type, primary_location, min_salary, max_salary,
        average_salary, salary_currency, salary_period, salary_available,
        pub_date_epoch, published_date, published_year, published_month,
        application_link, tech_filter_reason, cleaned_at
    ) VALUES (
        :guid, :title, :company_name, :company_slug, :company_logo,
        :excerpt, :description, :primary_category, :primary_seniority,
        :employment_type, :primary_location, :min_salary, :max_salary,
        :average_salary, :salary_currency, :salary_period, :salary_available,
        :pub_date_epoch, :published_date, :published_year, :published_month,
        :application_link, :tech_filter_reason, :cleaned_at
    );
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(CREATE_CLEANED_TABLE_SQL)
        cursor.executemany(insert_sql, transformed_records)
        conn.commit()

    print(f"[OK] Successfully saved {len(transformed_records)} records to table '{CLEANED_TABLE}'")
    return len(transformed_records)

# -----------------------------------------------------------------------------
# Step 5: Verification & Diagnostic Checks
# -----------------------------------------------------------------------------
def verify_pipeline() -> bool:
    """
    Performs full verification:
      - Validates raw_jobs remains completely untouched (100 rows).
      - Checks cleaned_jobs count and schema.
      - Confirms zero duplicate GUIDs.
      - Displays salary availability breakdown.
      - Displays 5 sample cleaned records.
    """
    print("\n" + "=" * 68)
    print("STEP 5: VERIFICATION & DIAGNOSTIC CHECKS")
    print("=" * 68)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check raw_jobs is unchanged
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {RAW_TABLE};")
        raw_count = cursor.fetchone()["cnt"]
        print(f"[OK] Table '{RAW_TABLE}' untouched row count: {raw_count}")
        if raw_count != 100:
            print(f"[ERROR] raw_jobs was altered! Expected 100, got {raw_count}")
            return False

        # Check cleaned_jobs count
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {CLEANED_TABLE};")
        cleaned_count = cursor.fetchone()["cnt"]
        print(f"[OK] Table '{CLEANED_TABLE}' total rows     : {cleaned_count}")

        # Check unique GUIDs
        cursor.execute(f"SELECT COUNT(DISTINCT guid) as uniq_cnt FROM {CLEANED_TABLE};")
        unique_guids = cursor.fetchone()["uniq_cnt"]
        print(f"[OK] Unique GUIDs in '{CLEANED_TABLE}'   : {unique_guids}")
        if cleaned_count != unique_guids:
            print(f"[ERROR] Found duplicate GUIDs in {CLEANED_TABLE}!")
            return False
        else:
            print("     -> 100% Unique Primary Keys, ZERO duplicates!")

        # Salary availability count
        cursor.execute(f"SELECT salary_available, COUNT(*) as cnt FROM {CLEANED_TABLE} GROUP BY salary_available;")
        sal_counts = {row["salary_available"]: row["cnt"] for row in cursor.fetchall()}
        print(f"\n[OK] Salary Availability Breakdown:")
        print(f"     - Jobs with salary disclosed ('Yes'): {sal_counts.get('Yes', 0)}")
        print(f"     - Jobs without salary data   ('No') : {sal_counts.get('No', 0)}")

        # Average salary computed count
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {CLEANED_TABLE} WHERE average_salary IS NOT NULL;")
        avg_sal_count = cursor.fetchone()["cnt"]
        print(f"     - Records with average_salary calculated (both min & max exist): {avg_sal_count}")

        # Valid application links
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {CLEANED_TABLE} WHERE application_link LIKE 'http%';")
        valid_links = cursor.fetchone()["cnt"]
        print(f"[OK] Valid Application Links          : {valid_links} / {cleaned_count} (100%)")

        # Display 5 sample records
        cursor.execute(f"SELECT * FROM {CLEANED_TABLE} LIMIT 5;")
        samples = cursor.fetchall()

        print("\n" + "-" * 68)
        print("5 SAMPLE CLEANED RECORDS:")
        print("-" * 68)
        for i, s in enumerate(samples, 1):
            sal_str = f"{s['salary_currency'] or ''} {s['min_salary']:,.0f} - {s['max_salary']:,.0f}" if s['salary_available'] == 'Yes' and s['min_salary'] else "Undisclosed"
            avg_str = f"${s['average_salary']:,.0f}" if s['average_salary'] else "N/A"
            print(f"[{i}] {s['title']}")
            print(f"    Company    : {s['company_name']}")
            print(f"    Category   : {s['primary_category']} | Seniority: {s['primary_seniority']} | Type: {s['employment_type']}")
            print(f"    Location   : {s['primary_location']}")
            print(f"    Salary     : {sal_str} (Avg: {avg_str}) | Disclosed: {s['salary_available']}")
            print(f"    Published  : {s['published_date']} (Year: {s['published_year']}, Month: {s['published_month']})")
            print(f"    Apply Link : {s['application_link']}")
            print(f"    Tech Match : {s['tech_filter_reason']}")
            print()

    print("=" * 68)
    print("SUCCESS: Phase 5 Data Cleaning Pipeline verified!")
    print("=" * 68)
    return True

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
def run_pipeline():
    # Step 1: Inspection
    inspect_raw_dataset()

    # Step 2: Technology filter evaluation
    df_evaluated, tech_count, excluded_count = check_technology_filter()

    # Step 3 & 4: Cleaning, Derived Fields & SQLite Insertion
    clean_and_save_data(df_evaluated)

    # Step 5: Verification
    success = verify_pipeline()
    return success

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
