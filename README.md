# JobInsight – Web-Based Job Market Data Collection, Analysis & Visualization Platform

**A 2-Credit College Mini-Project | B.Tech CSE (AI/ML)**

---

## 1. Project Overview

### Problem Statement
The modern remote technology job market is fast-moving, fragmented, and difficult for students and job seekers to analyze as a whole. Job postings are scattered across multiple boards, with opaque compensation disclosures, inconsistent experience requirements, and differing geographic restrictions.

### Project Objective
**JobInsight** is an end-to-end data engineering and analytics web application that:
1. Collects live remote job listings from the official **Himalayas Public Jobs API**.
2. Stores listings locally in a lightweight SQLite database.
3. Cleans, normalizes, and structures raw job metadata using Python and Pandas.
4. Generates data-driven market statistics (top categories, seniority distributions, salary transparency, hiring companies).
5. Visualizes findings via an interactive web dashboard with interactive Plotly charts.
6. Provides an interactive Job Explorer allowing users to search, filter, and inspect original job application links.

---

## 2. Technology Stack

* **Programming Language:** Python 3.14
* **Web Data Collection:** `requests` (with cursor-based pagination and custom User-Agent headers)
* **Local Data Storage:** SQLite (`sqlite3`)
* **Data Processing & Analytics:** `pandas`
* **Web Backend:** `fastapi` + `uvicorn`
* **Frontend / Templating:** HTML5, CSS3, JavaScript (Fetch API), Jinja2
* **Data Visualization:** Plotly.js (interactive client-side charts)

---

## 3. Current Development Phase

* **Current Status:** **Phase 9 — Final Polish Completed**
  - Project directory structure established.
  - Isolated Python virtual environment created and tested.
  - Core dependencies installed.
  - Central configuration file (`config.py`) created.
  - API connection and cursor pagination verified (`test_api.py`).
  - Data collector (`collector.py`) implemented and collected 100 real remote jobs into `data/raw_jobs.json`.
  - SQLite database module (`database.py`) implemented (`data/jobinsight.db`), safely storing 100 raw listings.
  - Data cleaning pipeline (`cleaner.py`) created: inspected dataset distributions, applied transparent deterministic technology filter (retained 47 tech jobs, excluded 53 non-tech roles), handled missing salaries honestly without imputation, normalized dates and strings, and populated `cleaned_jobs` table while preserving `raw_jobs`.
  - Analytical engine (`analysis.py`) implemented: modular, reusable functions for KPIs, category/seniority/employment distributions, top hiring locations & employers, salary metrics, and timeline trends.
  - Web dashboard (`main.py`, `templates/index.html`, `static/css/style.css`, `static/js/dashboard.js`) built with FastAPI, Jinja2, vanilla JS, and Plotly.js. Verified all 8 REST endpoints and live UI at `http://127.0.0.1:8000`.
  - Job Explorer (`GET /api/jobs`, `GET /api/job-filters`) added with search, 4-filter dropdowns, and cursor-safe pagination. All 11 Phase 8 verification checks passed (47 total jobs, Developer=20, Senior=33, India=3, no `raw_json` exposure, zero XSS vectors).
  - Phase 9 final polish completed: Robust chart loading & error handling, "Key Insights" section (5 verified cards), "India Focus" widget with 1-click filter navigation, and responsive mobile enhancements.

### Planned Phases
1. [x] **Phase 1:** Project Setup & Environment
2. [x] **Phase 2:** API Connection & Verification
3. [x] **Phase 3:** Data Collection Module (100 jobs collected)
4. [x] **Phase 4:** SQLite Storage (`data/jobinsight.db` populated)
5. [x] **Phase 5:** Data Cleaning Pipeline (`cleaned_jobs` populated with 47 tech jobs)
6. [x] **Phase 6:** Data Analysis & Aggregation Engine (`analysis.py` verified)
7. [x] **Phase 7:** Web Backend & Dashboard UI (`http://127.0.0.1:8000`)
8. [x] **Phase 8:** Job Explorer — `GET /api/jobs` + `GET /api/job-filters` (search, filter, pagination; all 11 checks passed)
9. [x] **Phase 9:** Final Polish — Key Insights, India Focus, Robust Chart Overlays & Responsive Layout

10. [ ] **Phase 10:** UI Polishing & Attribution
11. [ ] **Phase 11:** Documentation & Viva Guide

---

## 4. How to Run (Local Setup)

### 1. Activate the Virtual Environment
On Windows (PowerShell):
```powershell
cd C:\Users\ASUS\.gemini\antigravity\scratch\JobInsight
.\venv\Scripts\Activate.ps1
```

### 2. Verify Environment & Config
```powershell
python test_env.py
```

---

## 5. Data Source Attribution
This project strictly uses the public API provided by Himalayas:
* **Source:** Himalayas Remote Jobs API
* **API Documentation:** [https://himalayas.app/api](https://himalayas.app/api)
* **Website:** [https://himalayas.app](https://himalayas.app)
