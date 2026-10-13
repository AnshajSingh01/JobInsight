/**
 * JobInsight - Dashboard Frontend Client
 * -------------------------------------
 * Handles asynchronous data fetching from FastAPI REST endpoints
 * and renders KPI cards and interactive Plotly.js charts.
 */

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});

async function initDashboard() {
  // Load KPIs first
  loadKPIs();

  // Load Charts asynchronously in parallel
  loadCategoryChart();
  loadSeniorityChart();
  loadEmploymentChart();
  loadLocationChart();
  loadCompaniesChart();
  loadSalaryChart();
  loadTimelineChart();

  // Initialize Job Explorer (Phase 8)
  initJobExplorer();
}


/**
 * Universal Plotly layout theme for clean, consistent styling
 */
function getBasePlotlyLayout(overrides = {}) {
  return {
    margin: { t: 20, r: 20, b: 50, l: 60 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: {
      family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      color: "#475569",
      size: 12
    },
    hoverlabel: {
      bgcolor: "#0f172a",
      font: { color: "#ffffff", size: 12 },
      bordercolor: "#0f172a"
    },
    xaxis: {
      gridcolor: "#f1f5f9",
      zerolinecolor: "#e2e8f0"
    },
    yaxis: {
      gridcolor: "#f1f5f9",
      zerolinecolor: "#e2e8f0"
    },
    ...overrides
  };
}

const PLOTLY_CONFIG = {
  responsive: true,
  displayModeBar: false
};

function renderError(elementId, message) {
  const container = document.getElementById(elementId);
  if (container) {
    // Remove any loading overlay first
    const overlays = container.querySelectorAll(".chart-spinner-overlay, .spinner-wrapper");
    overlays.forEach(o => o.remove());
    container.innerHTML = `<div class="error-msg">⚠️ Unable to load data: ${message}</div>`;
  }
}

/**
 * Removes the loading overlay from a chart container after Plotly renders.
 * Ensures the overlay is completely removed from the DOM.
 */
function hideChartSpinner(elementId) {
  const container = document.getElementById(elementId);
  if (!container) return;
  const overlays = container.querySelectorAll(".chart-spinner-overlay, .spinner-wrapper");
  overlays.forEach(overlay => overlay.remove());
}

/**
 * 1. Fetch & populate Top KPI Cards
 */
async function loadKPIs() {
  try {
    const res = await fetch("/api/kpis");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    document.getElementById("kpi-total-jobs").textContent = data.total_jobs || "0";
    document.getElementById("kpi-companies").textContent = data.total_companies || "0";
    document.getElementById("kpi-salary").textContent = data.jobs_with_salary || "0";
    document.getElementById("kpi-salary-subtext").textContent = `${data.salary_coverage_pct}% transparency rate`;
    document.getElementById("kpi-category").textContent = data.top_category || "N/A";
    document.getElementById("kpi-seniority").textContent = data.top_seniority || "N/A";
  } catch (err) {
    console.error("Failed to load KPIs:", err);
    document.getElementById("kpi-total-jobs").textContent = "Err";
  }
}

/**
 * 2. Jobs by Category Chart (Bar Chart)
 */
async function loadCategoryChart() {
  const containerId = "chart-category";
  try {
    const res = await fetch("/api/category");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const categories = data.map(d => d.category);
    const counts = data.map(d => d.count);

    const trace = {
      x: categories,
      y: counts,
      type: "bar",
      marker: {
        color: "#3b82f6",
        opacity: 0.9,
        line: { color: "#2563eb", width: 1.5 }
      },
      hovertemplate: "<b>%{x}</b><br>Listings: %{y}<extra></extra>"
    };

    const layout = getBasePlotlyLayout({
      margin: { t: 20, r: 20, b: 110, l: 50 },
      xaxis: {
        tickangle: -40,
        automargin: true,
        gridcolor: "#f1f5f9"
      },
      yaxis: {
        title: "Number of Jobs",
        gridcolor: "#f1f5f9"
      }
    });

    Plotly.newPlot(containerId, [trace], layout, PLOTLY_CONFIG);
    hideChartSpinner(containerId);
  } catch (err) {
    console.error("Failed to load Category chart:", err);
    renderError(containerId, err.message);
  }
}

/**
 * 3. Jobs by Seniority Level Chart (Bar Chart)
 */
async function loadSeniorityChart() {
  const containerId = "chart-seniority";
  try {
    const res = await fetch("/api/seniority");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const levels = data.map(d => d.seniority);
    const counts = data.map(d => d.count);

    const trace = {
      x: levels,
      y: counts,
      type: "bar",
      marker: {
        color: "#8b5cf6",
        opacity: 0.9,
        line: { color: "#7c3aed", width: 1.5 }
      },
      hovertemplate: "<b>%{x}</b><br>Demand: %{y} roles<extra></extra>"
    };

    const layout = getBasePlotlyLayout({
      margin: { t: 20, r: 20, b: 50, l: 50 },
      yaxis: {
        title: "Number of Jobs",
        gridcolor: "#f1f5f9"
      }
    });

    Plotly.newPlot(containerId, [trace], layout, PLOTLY_CONFIG);
    hideChartSpinner(containerId);
  } catch (err) {
    console.error("Failed to load Seniority chart:", err);
    renderError(containerId, err.message);
  }
}

/**
 * 4. Employment Type Distribution (Donut Chart)
 */
async function loadEmploymentChart() {
  const containerId = "chart-employment";
  try {
    const res = await fetch("/api/employment");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const labels = data.map(d => d.employment_type);
    const values = data.map(d => d.count);

    const trace = {
      labels: labels,
      values: values,
      type: "pie",
      hole: 0.55,
      marker: {
        colors: ["#2563eb", "#10b981", "#f59e0b", "#64748b"]
      },
      textinfo: "label+percent",
      textposition: "outside",
      automargin: true,
      hovertemplate: "<b>%{label}</b><br>Share: %{percent} (%{value} jobs)<extra></extra>"
    };

    const layout = {
      margin: { t: 20, r: 20, b: 30, l: 20 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      showlegend: false,
      font: {
        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        color: "#475569"
      }
    };

    Plotly.newPlot(containerId, [trace], layout, PLOTLY_CONFIG);
    hideChartSpinner(containerId);
  } catch (err) {
    console.error("Failed to load Employment chart:", err);
    renderError(containerId, err.message);
  }
}

/**
 * 5. Top Hiring Locations (Horizontal Bar Chart)
 */
async function loadLocationChart() {
  const containerId = "chart-location";
  try {
    const res = await fetch("/api/location?limit=8");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Reverse for top-down display in horizontal bar
    const locations = data.map(d => d.location).reverse();
    const counts = data.map(d => d.count).reverse();

    const trace = {
      x: counts,
      y: locations,
      type: "bar",
      orientation: "h",
      marker: {
        color: "#0d9488",
        opacity: 0.9,
        line: { color: "#0f766e", width: 1.5 }
      },
      hovertemplate: "<b>%{y}</b><br>Available Jobs: %{x}<extra></extra>"
    };

    const layout = getBasePlotlyLayout({
      margin: { t: 20, r: 20, b: 50, l: 120 },
      xaxis: {
        title: "Number of Listings",
        gridcolor: "#f1f5f9"
      }
    });

    Plotly.newPlot(containerId, [trace], layout, PLOTLY_CONFIG);
    hideChartSpinner(containerId);
  } catch (err) {
    console.error("Failed to load Location chart:", err);
    renderError(containerId, err.message);
  }
}

/**
 * 6. Top Companies (Horizontal Bar Chart)
 */
async function loadCompaniesChart() {
  const containerId = "chart-companies";
  try {
    const res = await fetch("/api/companies?limit=8");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const companies = data.map(d => d.company).reverse();
    const counts = data.map(d => d.count).reverse();

    const trace = {
      x: counts,
      y: companies,
      type: "bar",
      orientation: "h",
      marker: {
        color: "#6366f1",
        opacity: 0.9,
        line: { color: "#4f46e5", width: 1.5 }
      },
      hovertemplate: "<b>%{y}</b><br>Openings: %{x}<extra></extra>"
    };

    const layout = getBasePlotlyLayout({
      margin: { t: 20, r: 20, b: 50, l: 140 },
      xaxis: {
        title: "Active Job Listings",
        gridcolor: "#f1f5f9",
        dtick: 1
      }
    });

    Plotly.newPlot(containerId, [trace], layout, PLOTLY_CONFIG);
    hideChartSpinner(containerId);
  } catch (err) {
    console.error("Failed to load Companies chart:", err);
    renderError(containerId, err.message);
  }
}

/**
 * 7. Annual Salary by Category (Bar Chart)
 * Strictly utilizes annual compensation records
 */
async function loadSalaryChart() {
  const containerId = "chart-salary";
  try {
    const res = await fetch("/api/salary");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const catData = data.by_category || [];
    if (catData.length === 0) {
      const container = document.getElementById(containerId);
      if (container) {
        hideChartSpinner(containerId);
        container.innerHTML += `<div class="spinner-wrapper" style="color: #64748b;"><span>No annual salary disclosures available.</span></div>`;
      }
      return;
    }

    const categories = catData.map(d => d.category);
    const avgSalaries = catData.map(d => d.avg_salary);
    const textLabels = avgSalaries.map(s => `$${(s / 1000).toFixed(0)}k`);

    const trace = {
      x: categories,
      y: avgSalaries,
      type: "bar",
      text: textLabels,
      textposition: "auto",
      marker: {
        color: "#10b981",
        opacity: 0.9,
        line: { color: "#059669", width: 1.5 }
      },
      hovertemplate: "<b>%{x}</b><br>Mean Annual Salary: $%{y:,.0f} USD<extra></extra>"
    };

    const layout = getBasePlotlyLayout({
      margin: { t: 20, r: 20, b: 60, l: 70 },
      yaxis: {
        title: "Average Salary (USD)",
        tickprefix: "$",
        gridcolor: "#f1f5f9"
      }
    });

    Plotly.newPlot(containerId, [trace], layout, PLOTLY_CONFIG);
    hideChartSpinner(containerId);
  } catch (err) {
    console.error("Failed to load Salary chart:", err);
    renderError(containerId, err.message);
  }
}

/**
 * 8. Dataset Publication Snapshot
 * All 47 jobs in this dataset share a single publication date because they were
 * collected in one batch. A bar chart would produce a single bar with a
 * micro-scale x-axis. Instead, render an honest summary card that presents the
 * actual data without fabricating a trend.
 */
async function loadTimelineChart() {
  const containerId = "chart-time";
  try {
    const res = await fetch("/api/time");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const daily = data.daily || [];
    // Compute totals from the real data — no fabrication
    const totalJobs = daily.reduce((sum, d) => sum + d.count, 0);
    const uniqueDates = daily.length;
    const primaryDate = daily.length > 0 ? daily[0].date : "N/A";

    const container = document.getElementById(containerId);
    if (!container) return;

    hideChartSpinner(containerId);

    container.innerHTML = `
      <div class="snapshot-card">
        <div class="snapshot-date-badge">📅 ${escapeHTML(primaryDate)}</div>
        <div class="snapshot-stat-row">
          <div class="snapshot-stat">
            <span class="snapshot-stat-value">${totalJobs}</span>
            <span class="snapshot-stat-label">Tech Jobs Published</span>
          </div>
          <div class="snapshot-stat">
            <span class="snapshot-stat-value">${uniqueDates}</span>
            <span class="snapshot-stat-label">Unique Publish Date${uniqueDates !== 1 ? "s" : ""}</span>
          </div>
          <div class="snapshot-stat">
            <span class="snapshot-stat-value">1</span>
            <span class="snapshot-stat-label">Collection Batch</span>
          </div>
        </div>
        <p class="snapshot-note">
          <strong>Note:</strong> All listings in this dataset were collected in a single API batch.
          They share the same publication date, so a trend chart would be misleading.
          This snapshot accurately represents the data as collected.
        </p>
      </div>
    `;
  } catch (err) {
    console.error("Failed to load Timeline chart:", err);
    renderError(containerId, err.message);
  }
}

/* ==========================================================================
   Job Explorer Functions (Phase 8)
   ========================================================================== */

let currentExplorerState = {
  search: "",
  category: "",
  seniority: "",
  employment_type: "",
  location: "",
  page: 1,
  limit: 10
};

let searchDebounceTimer = null;

function escapeHTML(str) {
  if (!str) return "";
  return String(str).replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

async function initJobExplorer() {
  await loadJobFilters();
  await loadJobs();

  // Search input debounced listener
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        currentExplorerState.search = e.target.value.trim();
        currentExplorerState.page = 1; // Reset to page 1 on search change
        loadJobs();
      }, 300);
    });
  }

  // Dropdown filter change listeners
  const filterMappings = [
    { id: "filter-category", key: "category" },
    { id: "filter-seniority", key: "seniority" },
    { id: "filter-employment", key: "employment_type" },
    { id: "filter-location", key: "location" }
  ];

  filterMappings.forEach(({ id, key }) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", (e) => {
        currentExplorerState[key] = e.target.value;
        currentExplorerState.page = 1; // Reset to page 1 on filter change
        loadJobs();
      });
    }
  });

  // Clear filters button
  const clearBtn = document.getElementById("clear-filters-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      clearFilters();
    });
  }

  // Explore India button (Phase 9)
  const exploreIndiaBtn = document.getElementById("btn-explore-india");
  if (exploreIndiaBtn) {
    exploreIndiaBtn.addEventListener("click", () => {
      // Set location filter to India
      currentExplorerState.location = "India";
      currentExplorerState.search = "";
      currentExplorerState.category = "";
      currentExplorerState.seniority = "";
      currentExplorerState.employment_type = "";
      currentExplorerState.page = 1;

      // Update UI dropdowns
      const locSelect = document.getElementById("filter-location");
      if (locSelect) locSelect.value = "India";

      const searchInput = document.getElementById("search-input");
      if (searchInput) searchInput.value = "";

      const otherSelects = ["filter-category", "filter-seniority", "filter-employment"];
      otherSelects.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });

      // Reload jobs
      loadJobs();

      // Smooth scroll to Job Explorer section
      const explorerSection = document.getElementById("job-explorer");
      if (explorerSection) {
        explorerSection.scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  // Pagination buttons
  const prevBtn = document.getElementById("prev-page-btn");
  const nextBtn = document.getElementById("next-page-btn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (currentExplorerState.page > 1) {
        currentExplorerState.page -= 1;
        loadJobs();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      currentExplorerState.page += 1;
      loadJobs();
    });
  }
}

async function loadJobFilters() {
  try {
    const res = await fetch("/api/job-filters");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    populateSelect("filter-category", data.categories, "All Categories");
    populateSelect("filter-seniority", data.seniorities, "All Seniorities");
    populateSelect("filter-employment", data.employment_types, "All Contract Types");
    populateSelect("filter-location", data.locations, "All Locations");
  } catch (err) {
    console.error("Failed to load job filters:", err);
  }
}

function populateSelect(selectId, items, defaultLabel) {
  const select = document.getElementById(selectId);
  if (!select || !Array.isArray(items)) return;

  select.innerHTML = `<option value="">${escapeHTML(defaultLabel)}</option>`;
  items.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    select.appendChild(opt);
  });
}

async function loadJobs() {
  const container = document.getElementById("jobs-container");
  if (!container) return;

  container.innerHTML = `
    <div class="spinner-wrapper" style="height: 180px;">
      <div class="spinner"></div>
      <span>Filtering job listings...</span>
    </div>`;

  try {
    const params = new URLSearchParams();
    if (currentExplorerState.search) params.append("search", currentExplorerState.search);
    if (currentExplorerState.category) params.append("category", currentExplorerState.category);
    if (currentExplorerState.seniority) params.append("seniority", currentExplorerState.seniority);
    if (currentExplorerState.employment_type) params.append("employment_type", currentExplorerState.employment_type);
    if (currentExplorerState.location) params.append("location", currentExplorerState.location);
    params.append("page", currentExplorerState.page);
    params.append("limit", currentExplorerState.limit);

    const res = await fetch(`/api/jobs?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    renderJobs(data);
  } catch (err) {
    console.error("Failed to load jobs:", err);
    container.innerHTML = `<div class="error-msg">⚠️ Failed to load jobs: ${escapeHTML(err.message)}</div>`;
  }
}

function renderJobs(data) {
  const container = document.getElementById("jobs-container");
  const showingCount = document.getElementById("showing-count");
  const totalCount = document.getElementById("total-count");
  const pageIndicator = document.getElementById("page-indicator");
  const prevBtn = document.getElementById("prev-page-btn");
  const nextBtn = document.getElementById("next-page-btn");

  const jobs = data.jobs || [];
  const totalJobs = data.total_jobs || 0;
  const page = data.page || 1;
  const totalPages = data.total_pages || 1;

  if (showingCount) showingCount.textContent = jobs.length;
  if (totalCount) totalCount.textContent = totalJobs;
  if (pageIndicator) pageIndicator.textContent = `Page ${page} of ${totalPages}`;

  if (prevBtn) prevBtn.disabled = (page <= 1);
  if (nextBtn) nextBtn.disabled = (page >= totalPages);

  if (jobs.length === 0) {
    container.innerHTML = `
      <div class="no-jobs">
        <h3>No matching technology jobs found</h3>
        <p>Try searching for different keywords or clear your active filters.</p>
      </div>`;
    return;
  }

  const html = jobs.map(job => {
    const title = escapeHTML(job.title);
    const company = escapeHTML(job.company_name);
    const category = escapeHTML(job.primary_category);
    const seniority = escapeHTML(job.primary_seniority);
    const employment = escapeHTML(job.employment_type);
    const location = escapeHTML(job.primary_location);
    const published = escapeHTML(job.published_date);
    const link = encodeURI(job.application_link);

    // Salary formatting
    let salaryBadge = `<span class="badge salary">Undisclosed Salary</span>`;
    if (job.salary_available === "Yes") {
      const cur = escapeHTML(job.salary_currency || "USD");
      const period = escapeHTML(job.salary_period || "annual");
      if (job.min_salary && job.max_salary) {
        salaryBadge = `<span class="badge salary">${cur} ${Number(job.min_salary).toLocaleString()} - ${Number(job.max_salary).toLocaleString()} (${period})</span>`;
      } else if (job.min_salary) {
        salaryBadge = `<span class="badge salary">${cur} ${Number(job.min_salary).toLocaleString()}+ (${period})</span>`;
      }
    }

    // Company logo or letter fallback
    const logoHtml = job.company_logo
      ? `<img src="${encodeURI(job.company_logo)}" alt="${company} logo" class="job-logo" onerror="this.onerror=null; this.outerHTML='<div class=\\'job-logo-fallback\\'>${company.charAt(0)}</div>';">`
      : `<div class="job-logo-fallback">${company.charAt(0)}</div>`;

    return `
      <article class="job-card">
        <div class="job-main">
          ${logoHtml}
          <div class="job-details">
            <h3 class="job-title">${title}</h3>
            <div class="job-meta-row">
              <strong>${company}</strong> &bull; 📍 ${location} &bull; 🗓️ ${published}
            </div>
            <div class="job-tags-row">
              <span class="badge category">${category}</span>
              <span class="badge seniority">${seniority}</span>
              <span class="badge employment">${employment}</span>
              ${salaryBadge}
            </div>
          </div>
        </div>
        <div class="job-action">
          <a href="${link}" target="_blank" rel="noopener noreferrer" class="btn-view-job">View Job &rarr;</a>
        </div>
      </article>
    `;
  }).join("");

  container.innerHTML = html;
}

function clearFilters() {
  currentExplorerState.search = "";
  currentExplorerState.category = "";
  currentExplorerState.seniority = "";
  currentExplorerState.employment_type = "";
  currentExplorerState.location = "";
  currentExplorerState.page = 1;

  const searchInput = document.getElementById("search-input");
  if (searchInput) searchInput.value = "";

  const selects = ["filter-category", "filter-seniority", "filter-employment", "filter-location"];
  selects.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });

  loadJobs();
}

