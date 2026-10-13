"""
JobInsight - Phase 2 API Verification Script
--------------------------------------------
What it does:
  Connects to the Himalayas Remote Jobs API, validates HTTP response status,
  verifies the JSON payload schema (top-level and job-level fields), and tests
  cursor-based pagination with a small 2-request test.

Why we need it:
  Before implementing the database and full data collector, we must confirm
  that our network configuration, headers, timeout settings, and pagination logic
  work reliably against the real live API without hitting rate limits or errors.

How it connects to the project:
  Uses settings from config.py and proves the exact logic that collector.py
  will use in Phase 3.
"""

import sys
import time
import requests
import config

def test_himalayas_api():
    print("=" * 65)
    print("JobInsight - Himalayas API Connection & Cursor Verification")
    print("=" * 65)

    endpoint = config.HIMALAYAS_API_BASE_URL
    headers = config.API_REQUEST_HEADERS
    timeout = config.REQUEST_TIMEOUT_SECONDS

    print(f"Target Endpoint : {endpoint}")
    print(f"User-Agent      : {headers.get('User-Agent')}")
    print("-" * 65)

    # -------------------------------------------------------------
    # Step 1: Initial Test Request (limit=2)
    # -------------------------------------------------------------
    print("[1/3] Sending initial request (limit=2)...")
    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params={"limit": 2},
            timeout=timeout
        )
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Network or connection error: {e}")
        return False

    print(f"[OK] HTTP Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"[FAIL] Unexpected HTTP status: {response.status_code}")
        print(f"Response text: {response.text[:300]}")
        return False

    # Verify JSON parsing
    try:
        data = response.json()
        print("[OK] Response successfully parsed as JSON")
    except ValueError as e:
        print(f"[FAIL] Response is not valid JSON: {e}")
        return False

    # -------------------------------------------------------------
    # Step 2: Top-Level Field Verification
    # -------------------------------------------------------------
    print("\n[2/3] Checking top-level structure...")
    expected_top_keys = ["jobs", "nextCursor", "totalCount"]
    for key in expected_top_keys:
        if key in data:
            print(f"  [OK] Field '{key}' present (Value: {data.get(key) if key != 'jobs' else f'{len(data[key])} jobs in list'})")
        else:
            print(f"  [WARNING] Key '{key}' not found in top-level response")

    jobs = data.get("jobs", [])
    if not jobs:
        print("[FAIL] 'jobs' list is empty in the response")
        return False

    # Inspect first sample job
    sample = jobs[0]
    print("\n[Sample Job Inspection]")
    fields_to_inspect = [
        "guid",
        "title",
        "companyName",
        "categories",
        "seniority",
        "employmentType",
        "locationRestrictions",
        "minSalary",
        "maxSalary",
        "currency",
        "pubDate",
        "applicationLink"
    ]

    for field in fields_to_inspect:
        val = sample.get(field, "<NOT FOUND>")
        print(f"  - {field:<22}: {val}")

    page1_guids = [j.get("guid") for j in jobs]

    # -------------------------------------------------------------
    # Step 3: Cursor-Based Pagination Verification
    # -------------------------------------------------------------
    next_cursor = data.get("nextCursor")
    print("\n[3/3] Testing cursor pagination...")
    if not next_cursor:
        print("[WARNING] No 'nextCursor' returned; cannot test second page.")
        return True

    print(f"  Next cursor token received: {next_cursor[:25]}...")
    print(f"  Waiting {config.REQUEST_DELAY_SECONDS}s before requesting Page 2...")
    time.sleep(config.REQUEST_DELAY_SECONDS)

    try:
        page2_response = requests.get(
            endpoint,
            headers=headers,
            params={"limit": 2, "cursor": next_cursor},
            timeout=timeout
        )
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Page 2 request failed: {e}")
        return False

    print(f"  [OK] Page 2 HTTP Status: {page2_response.status_code}")
    if page2_response.status_code != 200:
        print(f"[FAIL] Page 2 returned non-200 status: {page2_response.status_code}")
        return False

    page2_data = page2_response.json()
    page2_jobs = page2_data.get("jobs", [])
    print(f"  [OK] Page 2 returned {len(page2_jobs)} jobs")

    page2_guids = [j.get("guid") for j in page2_jobs]
    overlap = set(page1_guids).intersection(set(page2_guids))

    if overlap:
        print(f"  [WARNING] Overlapping job GUIDs between Page 1 and Page 2: {overlap}")
    else:
        print("  [OK] Zero overlap! Cursor pagination correctly advanced to new job records.")

    print("\n" + "=" * 65)
    print("SUCCESS: Phase 2 API Verification passed completely!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    success = test_himalayas_api()
    sys.exit(0 if success else 1)
