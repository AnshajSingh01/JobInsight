"""
JobInsight - Phase 7 Web Backend (FastAPI)
------------------------------------------
What it does:
  Serves the HTML web dashboard via Jinja2 templates, mounts static files (CSS/JS),
  and provides REST API endpoints that return aggregated metrics computed by analysis.py.

Why we need it:
  Acts as the bridge between our backend data engine (SQLite + analysis.py) and
  the interactive browser frontend. Keeps the frontend decoupled from the database.

How it connects to the project:
  - Imports analysis functions from analysis.py.
  - Serves templates/index.html and static assets (static/css/style.css, static/js/dashboard.js).
  - Supplies JSON endpoints (/api/kpis, /api/category, etc.) consumed by dashboard.js.
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
import analysis

app = FastAPI(
    title="JobInsight API",
    description="Web-Based Job Market Data Collection, Analysis & Visualization Platform",
    version="1.0.0"
)

# Static files & Jinja2 templates setup
TEMPLATES_DIR = config.BASE_DIR / "templates"
STATIC_DIR = config.BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# -----------------------------------------------------------------------------
# Web Page Route
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """Renders the main analytics dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "himalayas_site_url": config.HIMALAYAS_SITE_URL,
            "himalayas_api_url": config.HIMALAYAS_API_BASE_URL
        }
    )


# -----------------------------------------------------------------------------
# REST API Endpoints (Delegates to analysis.py)
# -----------------------------------------------------------------------------
@app.get("/api/kpis")
async def api_kpis():
    """Returns top-level KPI metrics."""
    return JSONResponse(content=analysis.get_kpis())

@app.get("/api/category")
async def api_category():
    """Returns job distribution across technical categories."""
    return JSONResponse(content=analysis.get_jobs_by_category())

@app.get("/api/seniority")
async def api_seniority():
    """Returns job distribution across seniority levels."""
    return JSONResponse(content=analysis.get_jobs_by_seniority())

@app.get("/api/employment")
async def api_employment():
    """Returns job distribution across employment types."""
    return JSONResponse(content=analysis.get_jobs_by_employment_type())

@app.get("/api/location")
async def api_location(limit: int = 10):
    """Returns top geographic locations for remote jobs."""
    return JSONResponse(content=analysis.get_jobs_by_location(limit=limit))

@app.get("/api/companies")
async def api_companies(limit: int = 10):
    """Returns top hiring employers by listing volume."""
    return JSONResponse(content=analysis.get_top_companies(limit=limit))

@app.get("/api/salary")
async def api_salary():
    """Returns compensation statistics for disclosed salaries."""
    return JSONResponse(content=analysis.get_salary_analysis())

@app.get("/api/time")
async def api_time():
    """Returns posting activity over time."""
    return JSONResponse(content=analysis.get_jobs_over_time())

@app.get("/api/job-filters")
async def api_job_filters():
    """Returns dynamic available filter options for Job Explorer."""
    return JSONResponse(content=analysis.get_job_filters())

@app.get("/api/jobs")
async def api_jobs(
    search: str = None,
    category: str = None,
    seniority: str = None,
    employment_type: str = None,
    location: str = None,
    page: int = 1,
    limit: int = 10
):
    """
    Returns filtered, paginated jobs for the Job Explorer.
    Searches title and company_name with parameterized SQL.
    """
    results = analysis.search_jobs(
        search=search,
        category=category,
        seniority=seniority,
        employment_type=employment_type,
        location=location,
        page=page,
        limit=limit
    )
    return JSONResponse(content=results)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
