"""
JobInsight - Central Configuration Module
-----------------------------------------
This file stores all paths, API endpoints, headers, and operational settings
in a single location so that other modules don't hardcode magic values.
"""

import os
from pathlib import Path

# Base Directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DB_NAME = os.getenv("JOBINSIGHT_DB_NAME", "jobinsight.db")
DATABASE_PATH = DATA_DIR / DB_NAME

# Himalayas Public Jobs API Settings
# Documentation: https://himalayas.app/api
HIMALAYAS_API_BASE_URL = "https://himalayas.app/jobs/api"
HIMALAYAS_SEARCH_API_URL = "https://himalayas.app/jobs/api/search"
HIMALAYAS_SITE_URL = "https://himalayas.app"

# Himalayas requires a standard User-Agent header to avoid 403 Forbidden
DEFAULT_USER_AGENT = os.getenv(
    "JOBINSIGHT_USER_AGENT",
    "JobInsight-AcademicProject/1.0 (Mozilla/5.0; Windows NT 10.0; Win64; x64)"
)

# Request headers for the API collector
API_REQUEST_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "application/json"
}

# Ingestion Settings
MAX_JOBS_PER_REQUEST = 20  # Himalayas enforces max 20 per request
REQUEST_TIMEOUT_SECONDS = 15  # Network timeout for API requests
REQUEST_DELAY_SECONDS = 0.5  # Polite delay between paginated requests to respect rate limits
DEFAULT_TARGET_JOBS = 100  # Default number of jobs to collect in a single sync batch
RAW_JOBS_FILE = DATA_DIR / "raw_jobs.json"  # Raw collected data storage

