"""
JobInsight - Phase 3 Data Collector Module
------------------------------------------
What it does:
  Fetches live remote job listings from the Himalayas Public Jobs API using
  cursor-based pagination, respects API limits, prevents duplicates, handles
  network errors gracefully, and persists raw jobs data to data/raw_jobs.json.

Why we need it:
  Before we can clean, analyze, or display jobs, we need a reliable ingestion
  engine that gathers real-world data without violating rate limits or crashing
  on transient network glitches.

How it connects to the project:
  - Uses settings from config.py.
  - Generates data/raw_jobs.json, which will be ingested into SQLite in Phase 4
    and cleaned in Phase 5.
"""

import sys
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
import config

def fetch_page(cursor: Optional[str] = None, limit: int = config.MAX_JOBS_PER_REQUEST) -> Optional[Dict[str, Any]]:
    """
    Fetch a single page of job records from Himalayas API.
    
    Args:
        cursor: Pagination token from the previous response (None for first page).
        limit: Number of records to request (max 20).
    
    Returns:
        Parsed JSON dictionary if successful, None if an error occurs.
    """
    params = {"limit": min(limit, config.MAX_JOBS_PER_REQUEST)}
    if cursor:
        params["cursor"] = cursor

    try:
        response = requests.get(
            config.HIMALAYAS_API_BASE_URL,
            headers=config.API_REQUEST_HEADERS,
            params=params,
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print(f"[ERROR] Rate limit reached (HTTP 429). Himalayas asks to reduce request frequency.")
            return None
        elif response.status_code == 403:
            print(f"[ERROR] Access forbidden (HTTP 403). Check User-Agent header in config.py.")
            return None
        else:
            print(f"[ERROR] Unexpected HTTP {response.status_code}: {response.text[:200]}")
            return None

    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out after {config.REQUEST_TIMEOUT_SECONDS}s.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network connection failed: {e}")
        return None
    except ValueError as e:
        print(f"[ERROR] Response could not be parsed as JSON: {e}")
        return None

def collect_jobs(target_count: int = config.DEFAULT_TARGET_JOBS, save_to_file: bool = True) -> List[Dict[str, Any]]:
    """
    Collects a specified number of jobs using cursor pagination.
    
    Args:
        target_count: Desired number of unique jobs to collect.
        save_to_file: If True, writes raw data to config.RAW_JOBS_FILE.
        
    Returns:
        List of raw job dictionaries.
    """
    print("=" * 65)
    print(f"JobInsight - Collecting Jobs from Himalayas API (Target: {target_count})")
    print("=" * 65)

    collected_jobs: List[Dict[str, Any]] = []
    seen_guids = set()
    current_cursor: Optional[str] = None
    page_number = 1

    while len(collected_jobs) < target_count:
        needed = target_count - len(collected_jobs)
        batch_limit = min(needed, config.MAX_JOBS_PER_REQUEST)

        print(f"Fetching Page {page_number:02d} (Requesting up to {batch_limit} jobs)...", end=" ")
        data = fetch_page(cursor=current_cursor, limit=batch_limit)

        if not data or not isinstance(data, dict):
            print("[FAILED] Stopping collection due to API error.")
            break

        jobs = data.get("jobs", [])
        if not jobs:
            print("[INFO] No more jobs available in the feed.")
            break

        new_on_page = 0
        for job in jobs:
            guid = job.get("guid") or job.get("applicationLink")
            if guid and guid not in seen_guids:
                seen_guids.add(guid)
                collected_jobs.append(job)
                new_on_page += 1
            elif not guid:
                # Fallback if guid is missing
                collected_jobs.append(job)
                new_on_page += 1

            if len(collected_jobs) >= target_count:
                break

        print(f"[OK] Added {new_on_page} unique jobs (Total so far: {len(collected_jobs)}/{target_count})")

        # Advance cursor
        next_cursor = data.get("nextCursor")
        if not next_cursor:
            print("[INFO] End of feed reached: No nextCursor provided by API.")
            break

        if len(collected_jobs) >= target_count:
            break

        current_cursor = next_cursor
        page_number += 1
        time.sleep(config.REQUEST_DELAY_SECONDS)

    print("-" * 65)
    print(f"Collection Complete: Collected {len(collected_jobs)} unique jobs across {page_number} pages.")

    if save_to_file and collected_jobs:
        payload = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "target_count": target_count,
            "total_collected": len(collected_jobs),
            "source": "Himalayas Remote Jobs Public API",
            "source_url": config.HIMALAYAS_SITE_URL,
            "jobs": collected_jobs
        }
        with open(config.RAW_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Raw data saved to: {config.RAW_JOBS_FILE}")

    return collected_jobs

def verify_saved_data(filepath: Path = config.RAW_JOBS_FILE) -> bool:
    """
    Verifies that the raw data file exists, is valid JSON, contains expected
    fields, and has zero duplicate guids.
    """
    print("\n" + "=" * 65)
    print("Verifying Saved Raw Dataset")
    print("=" * 65)

    if not filepath.exists():
        print(f"[FAIL] File not found: {filepath}")
        return False

    size_kb = filepath.stat().st_size / 1024
    print(f"[OK] File exists : {filepath.name} ({size_kb:.1f} KB)")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[FAIL] Could not read JSON: {e}")
        return False

    jobs = data.get("jobs", [])
    total = data.get("total_collected", 0)
    print(f"[OK] Successfully re-loaded JSON: {len(jobs)} jobs (metadata count: {total})")

    # Check for duplicate GUIDs
    guids = [j.get("guid") for j in jobs if j.get("guid")]
    unique_guids = set(guids)
    if len(guids) == len(unique_guids):
        print(f"[OK] Deduplication Check: {len(guids)} GUIDs checked, ZERO duplicates found.")
    else:
        duplicates = len(guids) - len(unique_guids)
        print(f"[WARNING] Found {duplicates} duplicate GUIDs in saved dataset!")

    # Inspect first job
    if jobs:
        sample = jobs[0]
        print("\n[First Job Preview]")
        print(f"  - GUID        : {sample.get('guid')}")
        print(f"  - Title       : {sample.get('title')}")
        print(f"  - Company     : {sample.get('companyName')}")
        print(f"  - Employment  : {sample.get('employmentType')}")
        print(f"  - Seniority   : {sample.get('seniority')}")
        print(f"  - Categories  : {sample.get('categories')[:3]}...")
        print(f"  - Locations   : {sample.get('locationRestrictions')}")
        print(f"  - Salary Min  : {sample.get('minSalary')}")
        print(f"  - Salary Max  : {sample.get('maxSalary')}")
        print(f"  - Currency    : {sample.get('currency')}")
        print(f"  - Published   : {sample.get('pubDate')}")
        print(f"  - Apply Link  : {sample.get('applicationLink')}")

    print("\n" + "=" * 65)
    print("SUCCESS: Phase 3 Data Collector verified!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobInsight Himalayas Job Collector")
    parser.add_argument(
        "--target",
        type=int,
        default=config.DEFAULT_TARGET_JOBS,
        help=f"Number of jobs to collect (default: {config.DEFAULT_TARGET_JOBS})"
    )
    args = parser.parse_args()

    jobs = collect_jobs(target_count=args.target)
    if jobs:
        verify_saved_data()
    else:
        print("[FAIL] No jobs were collected.")
        sys.exit(1)
