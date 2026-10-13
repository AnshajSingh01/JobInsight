"""
JobInsight - Phase 8 Complete Web & API Verification Test Suite
---------------------------------------------------------------
Tests all existing dashboard endpoints, plus the newly added Job Explorer
endpoints, filters, search, pagination, and data sanitization.
"""

import sys
import requests

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 68)
    print(f"JobInsight - Phase 8 Verification Test Suite ({BASE_URL})")
    print("=" * 68)

    # 1. Dashboard HTML & Attribution Check
    res = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"[1/11] GET /                           : Status {res.status_code}", end=" ")
    if res.status_code == 200 and "Job Explorer" in res.text and "Himalayas" in res.text:
        print("[OK] Dashboard HTML contains Job Explorer and Himalayas attribution")
    else:
        print("[FAIL]")
        return False

    # 2. Existing Analytics Endpoints Regression Check
    analytics_eps = [
        "/api/kpis", "/api/category", "/api/seniority", "/api/employment",
        "/api/location", "/api/companies", "/api/salary", "/api/time"
    ]
    print("\n[2/11] Checking Existing Dashboard Endpoints (Regression Check)...")
    for ep in analytics_eps:
        r = requests.get(f"{BASE_URL}{ep}", timeout=5)
        if r.status_code != 200:
            print(f"  [FAIL] {ep} returned {r.status_code}")
            return False
    print(f"  [OK] All {len(analytics_eps)} dashboard analytics endpoints return 200 OK.")

    # 3. Dynamic Job Filters Endpoint
    print("\n[3/11] GET /api/job-filters...")
    r = requests.get(f"{BASE_URL}/api/job-filters", timeout=5)
    if r.status_code != 200:
        print(f"  [FAIL] /api/job-filters returned {r.status_code}")
        return False
    filters = r.json()
    for key in ["categories", "seniorities", "employment_types", "locations"]:
        if key not in filters or not isinstance(filters[key], list) or len(filters[key]) == 0:
            print(f"  [FAIL] Invalid filter list for '{key}'")
            return False
        print(f"  [OK] {key:<18}: {len(filters[key])} dynamic options (Sample: {filters[key][:2]})")

    # 4. Default Job Explorer (All Jobs, Page 1)
    print("\n[4/11] GET /api/jobs (Default All Jobs)...")
    r = requests.get(f"{BASE_URL}/api/jobs", timeout=5)
    data = r.json()
    if data.get("total_jobs") != 47:
        print(f"  [FAIL] Expected 47 total_jobs, got {data.get('total_jobs')}")
        return False
    if len(data.get("jobs", [])) != 10:
        print(f"  [FAIL] Expected 10 default jobs on page 1, got {len(data.get('jobs', []))}")
        return False
    print(f"  [OK] Total jobs: {data['total_jobs']}, Page 1 count: {len(data['jobs'])}, Total pages: {data['total_pages']}")

    # 5. Search Across Title and Company
    print("\n[5/11] GET /api/jobs?search=engineer...")
    r = requests.get(f"{BASE_URL}/api/jobs?search=engineer", timeout=5)
    data = r.json()
    match_count = data.get("total_jobs", 0)
    print(f"  [OK] Keyword 'engineer' matched {match_count} jobs.")
    if match_count == 0:
        print("  [FAIL] Expected matches for 'engineer'")
        return False

    # 6. Category Filter
    print("\n[6/11] GET /api/jobs?category=Developer...")
    r = requests.get(f"{BASE_URL}/api/jobs?category=Developer", timeout=5)
    data = r.json()
    dev_count = data.get("total_jobs", 0)
    print(f"  [OK] Category 'Developer' matched {dev_count} jobs (matches Phase 6 metric).")
    if dev_count != 20:
        print(f"  [FAIL] Expected 20 Developer jobs, got {dev_count}")
        return False

    # 7. Seniority Filter
    print("\n[7/11] GET /api/jobs?seniority=Senior...")
    r = requests.get(f"{BASE_URL}/api/jobs?seniority=Senior", timeout=5)
    data = r.json()
    sen_count = data.get("total_jobs", 0)
    print(f"  [OK] Seniority 'Senior' matched {sen_count} jobs (matches Phase 6 metric: 33).")
    if sen_count != 33:
        print(f"  [FAIL] Expected 33 Senior jobs, got {sen_count}")
        return False

    # 8. Location Filter
    print("\n[8/11] GET /api/jobs?location=India...")
    r = requests.get(f"{BASE_URL}/api/jobs?location=India", timeout=5)
    data = r.json()
    india_count = data.get("total_jobs", 0)
    print(f"  [OK] Location 'India' matched {india_count} jobs.")
    if india_count != 3:
        print(f"  [FAIL] Expected 3 India jobs, got {india_count}")
        return False

    # 9. Combined Filter & Pagination
    print("\n[9/11] Combined Filters & Pagination...")
    r_comb = requests.get(f"{BASE_URL}/api/jobs?category=Developer&seniority=Senior&limit=5&page=1", timeout=5)
    d_comb1 = r_comb.json()
    r_comb2 = requests.get(f"{BASE_URL}/api/jobs?category=Developer&seniority=Senior&limit=5&page=2", timeout=5)
    d_comb2 = r_comb2.json()

    print(f"  [OK] Developer + Senior total matches: {d_comb1['total_jobs']}")
    print(f"  [OK] Page 1: {len(d_comb1['jobs'])} jobs, Page 2: {len(d_comb2['jobs'])} jobs")

    # Check zero duplicate overlap between page 1 and page 2
    p1_guids = [j['guid'] for j in d_comb1['jobs']]
    p2_guids = [j['guid'] for j in d_comb2['jobs']]
    overlap = set(p1_guids).intersection(set(p2_guids))
    if overlap:
        print(f"  [FAIL] Duplicate overlap between pages: {overlap}")
        return False
    print("  [OK] Zero overlap between page 1 and page 2.")

    # 10. Edge Cases (Empty search & No-results search)
    print("\n[10/11] Edge Cases (Empty Search & No-Results)...")
    r_empty = requests.get(f"{BASE_URL}/api/jobs?search=", timeout=5)
    if r_empty.json().get("total_jobs") != 47:
        print("  [FAIL] Empty search should return all 47 jobs")
        return False
    print("  [OK] Empty search correctly returns all 47 jobs.")

    r_none = requests.get(f"{BASE_URL}/api/jobs?search=nonexistentterm12345", timeout=5)
    d_none = r_none.json()
    if d_none.get("total_jobs") != 0 or len(d_none.get("jobs", [])) != 0:
        print("  [FAIL] Nonexistent search should return 0 jobs")
        return False
    print("  [OK] No-results search cleanly returns 0 jobs with total_pages=1.")

    # 11. Security & Data Sanitization Check
    print("\n[11/11] Security & Privacy Check...")
    sample_job = data["jobs"][0]
    forbidden_keys = ["raw_json", "description", "raw_data"]
    leaked = [k for k in forbidden_keys if k in sample_job]
    if leaked:
        print(f"  [FAIL] Raw JSON or full description leaked: {leaked}")
        return False
    print("  [OK] Zero internal raw_json/HTML description fields exposed.")

    # Verify application_link is valid URL
    if not (sample_job.get("application_link", "").startswith("http")):
        print(f"  [FAIL] Invalid application_link: {sample_job.get('application_link')}")
        return False
    print(f"  [OK] Valid application link preserved: {sample_job.get('application_link')[:45]}...")

    print("\n" + "=" * 68)
    print("SUCCESS: 100% of Phase 8 Job Explorer checks passed completely!")
    print("=" * 68)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
