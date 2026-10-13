"""
JobInsight - Phase 6 Data Analysis & Aggregation Engine
-------------------------------------------------------
What it does:
  Provides modular, reusable data analysis functions that calculate key performance
  indicators (KPIs), frequency distributions, compensation metrics, and geographic
  patterns from the 'cleaned_jobs' SQLite table.

Why we need it:
  Decouples analytical logic from web presentation. Instead of embedding database queries
  inside web routes or frontend JavaScript, this dedicated analytics layer computes
  statistics reliably and returns clean Python dictionaries ready for FastAPI endpoints.

How it connects to the project:
  - Reads exclusively from 'cleaned_jobs' in data/jobinsight.db (populated in Phase 5).
  - Supplies structured metrics to main.py (FastAPI) in Phase 7 for dashboard KPI cards
    and Plotly charts.
"""

import sys
import sqlite3
from typing import Dict, Any, List, Optional
import pandas as pd
import config

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CLEANED_TABLE = "cleaned_jobs"

def get_connection() -> sqlite3.Connection:
    """Helper to obtain a SQLite database connection."""
    conn = sqlite3.connect(str(config.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def load_cleaned_dataframe() -> pd.DataFrame:
    """Loads the entire cleaned_jobs table into a Pandas DataFrame."""
    with get_connection() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {CLEANED_TABLE}", conn)
    return df

# -----------------------------------------------------------------------------
# 1. Overall KPIs
# -----------------------------------------------------------------------------
def get_kpis() -> Dict[str, Any]:
    """
    Computes top-level summary metrics across the technology job dataset.
    """
    df = load_cleaned_dataframe()
    total_jobs = len(df)

    if total_jobs == 0:
        return {
            "total_jobs": 0,
            "jobs_with_salary": 0,
            "jobs_without_salary": 0,
            "salary_coverage_pct": 0.0,
            "total_companies": 0,
            "top_category": "N/A",
            "top_seniority": "N/A",
            "top_employment_type": "N/A"
        }

    with_sal = int((df["salary_available"] == "Yes").sum())
    without_sal = int((df["salary_available"] == "No").sum())
    coverage_pct = round((with_sal / total_jobs) * 100, 1)
    unique_companies = int(df["company_name"].nunique())

    top_cat = df["primary_category"].mode()[0] if not df["primary_category"].empty else "N/A"
    top_sen = df["primary_seniority"].mode()[0] if not df["primary_seniority"].empty else "N/A"
    top_emp = df["employment_type"].mode()[0] if not df["employment_type"].empty else "N/A"

    return {
        "total_jobs": total_jobs,
        "jobs_with_salary": with_sal,
        "jobs_without_salary": without_sal,
        "salary_coverage_pct": coverage_pct,
        "total_companies": unique_companies,
        "top_category": top_cat,
        "top_seniority": top_sen,
        "top_employment_type": top_emp
    }

# -----------------------------------------------------------------------------
# 2. Jobs by Category
# -----------------------------------------------------------------------------
def get_jobs_by_category() -> List[Dict[str, Any]]:
    """
    Counts technology listings per primary category, sorted descending.
    """
    df = load_cleaned_dataframe()
    counts = df["primary_category"].value_counts().reset_index()
    counts.columns = ["category", "count"]
    counts["percentage"] = (counts["count"] / len(df) * 100).round(1)
    return counts.to_dict(orient="records")

# -----------------------------------------------------------------------------
# 3. Jobs by Seniority
# -----------------------------------------------------------------------------
def get_jobs_by_seniority() -> List[Dict[str, Any]]:
    """
    Counts listings by experience level, sorted descending.
    """
    df = load_cleaned_dataframe()
    counts = df["primary_seniority"].value_counts().reset_index()
    counts.columns = ["seniority", "count"]
    counts["percentage"] = (counts["count"] / len(df) * 100).round(1)
    return counts.to_dict(orient="records")

# -----------------------------------------------------------------------------
# 4. Jobs by Employment Type
# -----------------------------------------------------------------------------
def get_jobs_by_employment_type() -> List[Dict[str, Any]]:
    """
    Counts listings by employment contract type (Full Time, Contractor, etc.).
    """
    df = load_cleaned_dataframe()
    counts = df["employment_type"].value_counts().reset_index()
    counts.columns = ["employment_type", "count"]
    counts["percentage"] = (counts["count"] / len(df) * 100).round(1)
    return counts.to_dict(orient="records")

# -----------------------------------------------------------------------------
# 5. Jobs by Location (Top N)
# -----------------------------------------------------------------------------
def get_jobs_by_location(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Counts listings by geographic region, returning the top N locations.
    """
    df = load_cleaned_dataframe()
    counts = df["primary_location"].value_counts().head(limit).reset_index()
    counts.columns = ["location", "count"]
    counts["percentage"] = (counts["count"] / len(df) * 100).round(1)
    return counts.to_dict(orient="records")

# -----------------------------------------------------------------------------
# 6. Top Hiring Companies
# -----------------------------------------------------------------------------
def get_top_companies(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Identifies top hiring employers by listing volume.
    """
    df = load_cleaned_dataframe()
    counts = df["company_name"].value_counts().head(limit).reset_index()
    counts.columns = ["company", "count"]
    return counts.to_dict(orient="records")

# -----------------------------------------------------------------------------
# 7. Salary Analysis
# -----------------------------------------------------------------------------
def get_salary_analysis() -> Dict[str, Any]:
    """
    Calculates detailed compensation statistics strictly on disclosed records.
    Never treats missing salary as zero. Differentiates annual vs hourly compensation.
    """
    df = load_cleaned_dataframe()
    sal_df = df[df["average_salary"].notna()].copy()
    salary_count = len(sal_df)

    if salary_count == 0:
        return {
            "salary_count": 0,
            "overall_avg": None,
            "overall_min": None,
            "overall_max": None,
            "period_breakdown": {},
            "annual_stats": None,
            "by_category": [],
            "by_seniority": []
        }

    # Breakdown by compensation period (annual, hourly, monthly)
    period_counts = sal_df["salary_period"].value_counts().to_dict()

    # Annual salaries provide the most standardized metric for career analysis
    annual_df = sal_df[sal_df["salary_period"] == "annual"]
    annual_stats = None
    if len(annual_df) > 0:
        annual_stats = {
            "count": len(annual_df),
            "average": round(float(annual_df["average_salary"].mean()), 2),
            "median": round(float(annual_df["average_salary"].median()), 2),
            "min": round(float(annual_df["min_salary"].min()), 2),
            "max": round(float(annual_df["max_salary"].max()), 2)
        }

    # Overall metrics across all disclosed compensation records
    overall_avg = round(float(sal_df["average_salary"].mean()), 2)
    overall_min = round(float(sal_df["min_salary"].min()), 2)
    overall_max = round(float(sal_df["max_salary"].max()), 2)

    # Average salary by Category (for annual salaries to ensure fair comparison)
    by_cat_records = []
    if len(annual_df) > 0:
        cat_grp = annual_df.groupby("primary_category")["average_salary"].agg(["count", "mean", "min", "max"]).reset_index()
        cat_grp = cat_grp.sort_values(by="mean", ascending=False)
        for _, r in cat_grp.iterrows():
            by_cat_records.append({
                "category": r["primary_category"],
                "count": int(r["count"]),
                "avg_salary": round(float(r["mean"]), 2),
                "min_salary": round(float(r["min"]), 2),
                "max_salary": round(float(r["max"]), 2)
            })

    # Average salary by Seniority (for annual salaries)
    by_sen_records = []
    if len(annual_df) > 0:
        sen_grp = annual_df.groupby("primary_seniority")["average_salary"].agg(["count", "mean"]).reset_index()
        sen_grp = sen_grp.sort_values(by="mean", ascending=False)
        for _, r in sen_grp.iterrows():
            by_sen_records.append({
                "seniority": r["primary_seniority"],
                "count": int(r["count"]),
                "avg_salary": round(float(r["mean"]), 2)
            })

    return {
        "salary_count": salary_count,
        "overall_avg": overall_avg,
        "overall_min": overall_min,
        "overall_max": overall_max,
        "period_breakdown": period_counts,
        "annual_stats": annual_stats,
        "by_category": by_cat_records,
        "by_seniority": by_sen_records
    }

# -----------------------------------------------------------------------------
# 8. Jobs Over Time
# -----------------------------------------------------------------------------
def get_jobs_over_time() -> List[Dict[str, Any]]:
    """
    Aggregates job posting volumes chronologically by month and by date.
    """
    df = load_cleaned_dataframe()
    # Monthly aggregation
    monthly = df["published_month"].value_counts().reset_index()
    monthly.columns = ["period", "count"]
    monthly = monthly.sort_values(by="period", ascending=True)

    # Daily aggregation for finer timeline granularity
    daily = df["published_date"].value_counts().reset_index()
    daily.columns = ["date", "count"]
    daily = daily.sort_values(by="date", ascending=True)

    return {
        "monthly": monthly.to_dict(orient="records"),
        "daily": daily.to_dict(orient="records")
    }

# -----------------------------------------------------------------------------
# 9. Job Explorer - Dynamic Filters & Search
# -----------------------------------------------------------------------------
def get_job_filters() -> Dict[str, List[str]]:
    """
    Returns distinct available filter values dynamically from cleaned_jobs.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(f"SELECT DISTINCT primary_category FROM {CLEANED_TABLE} ORDER BY primary_category ASC;")
        categories = [r["primary_category"] for r in cursor.fetchall() if r["primary_category"]]

        cursor.execute(f"SELECT DISTINCT primary_seniority FROM {CLEANED_TABLE} ORDER BY primary_seniority ASC;")
        seniorities = [r["primary_seniority"] for r in cursor.fetchall() if r["primary_seniority"]]

        cursor.execute(f"SELECT DISTINCT employment_type FROM {CLEANED_TABLE} ORDER BY employment_type ASC;")
        employment_types = [r["employment_type"] for r in cursor.fetchall() if r["employment_type"]]

        cursor.execute(f"SELECT DISTINCT primary_location FROM {CLEANED_TABLE} ORDER BY primary_location ASC;")
        locations = [r["primary_location"] for r in cursor.fetchall() if r["primary_location"]]

    return {
        "categories": categories,
        "seniorities": seniorities,
        "employment_types": employment_types,
        "locations": locations
    }

def search_jobs(
    search: Optional[str] = None,
    category: Optional[str] = None,
    seniority: Optional[str] = None,
    employment_type: Optional[str] = None,
    location: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Searches and filters jobs with pagination using parameterized SQL queries.
    Never exposes raw_json or large HTML descriptions to client.
    """
    page = max(1, page)
    limit = max(1, min(limit, 50))
    offset = (page - 1) * limit

    conditions = []
    params = []

    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append("(title LIKE ? OR company_name LIKE ?)")
        params.extend([term, term])

    if category and category.strip():
        conditions.append("primary_category = ?")
        params.append(category.strip())

    if seniority and seniority.strip():
        conditions.append("primary_seniority = ?")
        params.append(seniority.strip())

    if employment_type and employment_type.strip():
        conditions.append("employment_type = ?")
        params.append(employment_type.strip())

    if location and location.strip():
        conditions.append("primary_location = ?")
        params.append(location.strip())

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) as count FROM {CLEANED_TABLE} {where_clause};"

    select_fields = """
        guid, title, company_name, company_slug, company_logo,
        primary_category, primary_seniority, employment_type, primary_location,
        salary_available, min_salary, max_salary, average_salary,
        salary_currency, salary_period, published_date, application_link
    """
    query_sql = f"""
        SELECT {select_fields}
        FROM {CLEANED_TABLE}
        {where_clause}
        ORDER BY pub_date_epoch DESC, guid ASC
        LIMIT ? OFFSET ?;
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(count_sql, params)
        total_jobs = cursor.fetchone()["count"]

        query_params = list(params) + [limit, offset]
        cursor.execute(query_sql, query_params)
        rows = [dict(r) for r in cursor.fetchall()]

    total_pages = (total_jobs + limit - 1) // limit if total_jobs > 0 else 1

    return {
        "jobs": rows,
        "page": page,
        "limit": limit,
        "total_jobs": total_jobs,
        "total_pages": total_pages
    }

# -----------------------------------------------------------------------------
# Terminal Report Generator
# -----------------------------------------------------------------------------

def print_report():
    """Generates a clean terminal presentation of all Phase 6 analytics."""
    print("=" * 68)
    print("JobInsight - Phase 6 Data Analysis Report")
    print("=" * 68)

    # KPIs
    kpis = get_kpis()
    print("\n[1] KEY PERFORMANCE INDICATORS (KPIs)")
    print(f"  - Total Technology Jobs     : {kpis['total_jobs']}")
    print(f"  - Unique Hiring Companies   : {kpis['total_companies']}")
    print(f"  - Disclosed Salary Listings : {kpis['jobs_with_salary']} ({kpis['salary_coverage_pct']}%)")
    print(f"  - Undisclosed Salary        : {kpis['jobs_without_salary']}")
    print(f"  - Top Job Category          : {kpis['top_category']}")
    print(f"  - Dominant Seniority Level  : {kpis['top_seniority']}")
    print(f"  - Main Employment Type      : {kpis['top_employment_type']}")

    # Categories
    cats = get_jobs_by_category()
    print("\n[2] JOBS BY CATEGORY")
    for c in cats:
        print(f"  - {c['category']:<28}: {c['count']:>2} listings ({c['percentage']:>4.1f}%)")

    # Seniority
    sens = get_jobs_by_seniority()
    print("\n[3] JOBS BY SENIORITY LEVEL")
    for s in sens:
        print(f"  - {s['seniority']:<28}: {s['count']:>2} listings ({s['percentage']:>4.1f}%)")

    # Employment Type
    emps = get_jobs_by_employment_type()
    print("\n[4] JOBS BY EMPLOYMENT TYPE")
    for e in emps:
        print(f"  - {e['employment_type']:<28}: {e['count']:>2} listings ({e['percentage']:>4.1f}%)")

    # Top Locations
    locs = get_jobs_by_location(limit=8)
    print("\n[5] TOP HIRING LOCATIONS")
    for loc in locs:
        print(f"  - {loc['location']:<28}: {loc['count']:>2} listings ({loc['percentage']:>4.1f}%)")

    # Top Companies
    comps = get_top_companies(limit=8)
    print("\n[6] TOP HIRING EMPLOYERS")
    for comp in comps:
        print(f"  - {comp['company']:<28}: {comp['count']:>2} openings")

    # Salary Analysis
    sal = get_salary_analysis()
    print("\n[7] SALARY ANALYSIS (DISCLOSED COMPENSATION ONLY)")
    print(f"  - Total Disclosed Salaries  : {sal['salary_count']}")
    print(f"  - Pay Frequency Breakdown   : {sal['period_breakdown']}")
    if sal['annual_stats']:
        ann = sal['annual_stats']
        print(f"  - Annual Compensation Stats :")
        print(f"      * Sample Size (Annual)  : {ann['count']} listings")
        print(f"      * Mean Annual Salary    : ${ann['average']:,.2f} USD")
        print(f"      * Median Annual Salary  : ${ann['median']:,.2f} USD")
        print(f"      * Minimum Annual Salary : ${ann['min']:,.2f} USD")
        print(f"      * Maximum Annual Salary : ${ann['max']:,.2f} USD")

    if sal['by_category']:
        print("\n  - Mean Annual Salary by Category:")
        for sc in sal['by_category']:
            print(f"      * {sc['category']:<22}: ${sc['avg_salary']:>10,.2f} (n={sc['count']})")

    if sal['by_seniority']:
        print("\n  - Mean Annual Salary by Seniority:")
        for ss in sal['by_seniority']:
            print(f"      * {ss['seniority']:<22}: ${ss['avg_salary']:>10,.2f} (n={ss['count']})")

    # Timeline
    timeline = get_jobs_over_time()
    print("\n[8] POSTING ACTIVITY OVER TIME")
    print("  - Monthly Distribution:")
    for m in timeline["monthly"]:
        print(f"      * {m['period']}: {m['count']} listings")
    print("  - Daily Distribution:")
    for d in timeline["daily"]:
        print(f"      * {d['date']}: {d['count']} listings")

# -----------------------------------------------------------------------------
# Verification Suite
# -----------------------------------------------------------------------------
def verify_analysis() -> bool:
    """
    Executes all Phase 6 sanity checks and prints verification results.
    """
    print("\n" + "=" * 68)
    print("PHASE 6 SANITY & MATHEMATICAL VERIFICATION")
    print("=" * 68)

    df = load_cleaned_dataframe()
    total = len(df)

    # 1. Row count check
    if total != 47:
        print(f"[FAIL] Expected 47 cleaned records, found: {total}")
        return False
    print(f"[OK] Record Count: Exactly 47 cleaned technology records verified.")

    # 2. Category sum check
    cats = get_jobs_by_category()
    cat_sum = sum(c["count"] for c in cats)
    if cat_sum != total:
        print(f"[FAIL] Category count sum ({cat_sum}) != total jobs ({total})")
        return False
    print(f"[OK] Category Sum Check: {cat_sum} == {total} (100% of records accounted for).")

    # 3. Seniority sum check
    sens = get_jobs_by_seniority()
    sen_sum = sum(s["count"] for s in sens)
    if sen_sum != total:
        print(f"[FAIL] Seniority count sum ({sen_sum}) != total jobs ({total})")
        return False
    print(f"[OK] Seniority Sum Check: {sen_sum} == {total} (100% of records accounted for).")

    # 4. Employment type sum check
    emps = get_jobs_by_employment_type()
    emp_sum = sum(e["count"] for e in emps)
    if emp_sum != total:
        print(f"[FAIL] Employment type sum ({emp_sum}) != total jobs ({total})")
        return False
    print(f"[OK] Employment Type Sum Check: {emp_sum} == {total} (100% accounted for).")

    # 5. Salary non-zero check
    sal = get_salary_analysis()
    if sal["salary_count"] != 18:
        print(f"[FAIL] Expected 18 salary records, got {sal['salary_count']}")
        return False
    # Ensure missing records weren't converted to 0
    raw_zeros = (df["average_salary"] == 0).sum()
    if raw_zeros > 0:
        print(f"[FAIL] Found {raw_zeros} records with average_salary == 0!")
        return False
    print(f"[OK] Salary Calculation Check: Exactly 18 disclosed records used; zero zero-imputations.")

    # 6. Sorting check
    cat_counts = [c["count"] for c in cats]
    if cat_counts != sorted(cat_counts, reverse=True):
        print(f"[FAIL] Category counts are not sorted descending!")
        return False
    print(f"[OK] Category Sorting: Confirmed descending order.")

    # 7. Timeline chronological check
    t_data = get_jobs_over_time()["monthly"]
    t_periods = [p["period"] for p in t_data]
    if t_periods != sorted(t_periods):
        print(f"[FAIL] Timeline is not sorted chronologically!")
        return False
    print(f"[OK] Chronological Ordering: Confirmed timeline dates ascending.")

    print("\n" + "=" * 68)
    print("SUCCESS: Phase 6 Analysis & Aggregation Engine fully verified!")
    print("=" * 68)
    return True

if __name__ == "__main__":
    print_report()
    success = verify_analysis()
    sys.exit(0 if success else 1)
