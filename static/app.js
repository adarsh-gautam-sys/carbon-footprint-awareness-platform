/* ============================================================
   Carbon Footprint Awareness Platform — Frontend Logic
   ============================================================ */

"use strict";

// ── DOM references ──────────────────────────────────────────
const form        = document.getElementById("footprint-form");
const statusEl    = document.getElementById("form-status");
const submitBtn   = document.getElementById("submit-btn");

const summaryEmpty  = document.getElementById("summary-empty");
const summaryData   = document.getElementById("summary-data");
const monthlyTotal  = document.getElementById("monthly-total");
const yearlyTotal   = document.getElementById("yearly-total");
const confidencePct = document.getElementById("confidence-pct");
const confidenceFill= document.getElementById("confidence-fill");
const confidenceBar = document.querySelector(".confidence-bar");
const methodNote    = document.getElementById("methodology-note");

const breakdownSection  = document.getElementById("breakdown-section");
const breakdownList     = document.getElementById("breakdown");
const actionsSection    = document.getElementById("actions-section");
const actionsContainer  = document.getElementById("actions");
const insightsSection   = document.getElementById("insights-section");
const insightsList      = document.getElementById("insights");
const contextSection    = document.getElementById("context-section");
const contextBars       = document.getElementById("context-bars");

// ── Category color map ──────────────────────────────────────
const CATEGORY_COLORS = {
  "Home energy":        "breakdown-fill-home",
  "Transport":          "breakdown-fill-transport",
  "Food and lifestyle": "breakdown-fill-food",
};

// Benchmark data (kg CO2e/year → converted to monthly for comparison)
const BENCHMARKS = [
  { name: "Paris 1.5°C target",  yearly_tonnes: 2.0,  cls: "context-paris" },
  { name: "World average",        yearly_tonnes: 4.7,  cls: "context-world" },
  { name: "India average",        yearly_tonnes: 1.9,  cls: "context-india" },
];

// ── Helpers ─────────────────────────────────────────────────
function numVal(formData, key) {
  const v = parseFloat(formData.get(key));
  return isNaN(v) ? 0 : Math.max(0, v);
}

function setStatus(text, type = "") {
  statusEl.textContent = text;
  statusEl.className = type;
}

function showSection(el) {
  el.classList.remove("hidden");
  el.classList.add("anim-in");
}

function effortClass(effort) {
  const map = { low: "effort-low", medium: "effort-medium", high: "effort-high" };
  return map[effort] ?? "effort-medium";
}

function escapeText(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(String(str)));
  return div.innerHTML;
}

// ── Build API payload from form ──────────────────────────────
function buildPayload(formData) {
  const name    = String(formData.get("name") || "Friend").trim().slice(0, 80);
  const country = String(formData.get("country") || "India").trim().slice(0, 80);
  const goal    = String(formData.get("goal") || "reduce_emissions");

  if (!name) throw new Error("Please enter your name.");
  if (!country) throw new Error("Please enter your country.");

  return {
    profile: { name, country, goal },
    home: {
      electricity_kwh:     numVal(formData, "electricity_kwh"),
      natural_gas_therms:  numVal(formData, "natural_gas_therms"),
      renewable_percent:   Math.min(100, numVal(formData, "renewable_percent")),
      household_size:      Math.max(1, Math.round(numVal(formData, "household_size")) || 1),
    },
    transport: [
      {
        mode:        String(formData.get("transport_mode") || "bus"),
        km_per_week: numVal(formData, "km_per_week"),
      },
    ],
    lifestyle: {
      diet:                String(formData.get("diet") || "mixed"),
      meals_out_per_week:  Math.round(numVal(formData, "meals_out_per_week")),
      new_items_per_month: Math.round(numVal(formData, "new_items_per_month")),
      waste_bags_per_week: Math.round(numVal(formData, "waste_bags_per_week")),
    },
  };
}

// ── Render breakdown bars ────────────────────────────────────
function renderBreakdown(categories) {
  const maxKg = Math.max(...categories.map(c => c.monthly_kg), 1);

  breakdownList.replaceChildren(
    ...categories.map((item) => {
      const pct = Math.round((item.monthly_kg / maxKg) * 100);
      const colorClass = CATEGORY_COLORS[item.category] ?? "breakdown-fill-default";

      const el = document.createElement("div");
      el.className = "breakdown-item";
      el.setAttribute("role", "listitem");
      el.innerHTML = `
        <div class="breakdown-header">
          <span class="breakdown-name">${escapeText(item.category)}</span>
          <span class="breakdown-value" aria-label="${escapeText(item.monthly_kg)} kg per month">${item.monthly_kg} kg/mo</span>
        </div>
        <div class="breakdown-bar-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"
             aria-label="${escapeText(item.category)} is ${pct}% of largest category">
          <div class="breakdown-bar-fill ${colorClass}" style="width:0%"></div>
        </div>
        <p class="breakdown-explanation">${escapeText(item.explanation)}</p>
      `;

      // Animate bar after paint
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const fill = el.querySelector(".breakdown-bar-fill");
          if (fill) fill.style.width = `${pct}%`;
        });
      });

      return el;
    })
  );
}

// ── Render action cards ──────────────────────────────────────
function renderActions(actions) {
  actionsContainer.replaceChildren(
    ...actions.map((item) => {
      const el = document.createElement("article");
      el.className = "card";
      el.setAttribute("role", "listitem");
      el.innerHTML = `
        <span class="card-title">${escapeText(item.title)}</span>
        <div class="card-meta">
          <span class="card-saving">saves ~${item.impact_kg_month} kg/mo</span>
          <span class="card-effort ${effortClass(item.effort)}">${escapeText(item.effort)} effort</span>
        </div>
        <p class="card-body">${escapeText(item.why_it_matters)}</p>
      `;
      return el;
    })
  );
}

// ── Render insights ──────────────────────────────────────────
function renderInsights(insights) {
  insightsList.replaceChildren(
    ...insights.map((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      return li;
    })
  );
}

// ── Render global comparison ─────────────────────────────────
function renderContext(yearlyTonnes) {
  const userMonthlyKg = (yearlyTonnes * 1000) / 12;

  // Max for bar scale: highest of user vs benchmarks
  const maxTonnes = Math.max(
    yearlyTonnes,
    ...BENCHMARKS.map(b => b.yearly_tonnes),
    0.1
  );

  const items = [
    { name: "You (this year)", yearly_tonnes: yearlyTonnes, cls: "context-you" },
    ...BENCHMARKS,
  ];

  contextBars.setAttribute("aria-label", `Your estimated yearly footprint compared to global benchmarks`);
  contextBars.replaceChildren(
    ...items.map(({ name, yearly_tonnes, cls }) => {
      const pct = Math.min(100, Math.round((yearly_tonnes / maxTonnes) * 100));
      const row = document.createElement("div");
      row.className = "context-row";
      row.setAttribute("role", "listitem");
      row.innerHTML = `
        <div class="context-label-row">
          <span class="context-name">${escapeText(name)}</span>
          <span class="context-value">${yearly_tonnes.toFixed(1)}t CO₂e/yr</span>
        </div>
        <div class="context-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"
             aria-label="${escapeText(name)}: ${yearly_tonnes.toFixed(1)} tonnes per year">
          <div class="context-fill ${cls}" style="width:0%"></div>
        </div>
      `;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const fill = row.querySelector(".context-fill");
          if (fill) fill.style.width = `${pct}%`;
        });
      });
      return row;
    })
  );
}

// ── Render full result ───────────────────────────────────────
function renderResult(result) {
  // Show summary
  summaryEmpty.classList.add("hidden");
  summaryData.classList.remove("hidden");
  summaryData.classList.add("anim-in");

  monthlyTotal.textContent = result.total_monthly_kg.toLocaleString();
  yearlyTotal.textContent  = result.total_yearly_tonnes.toFixed(2);

  const confPct = Math.round(result.confidence_score * 100);
  confidencePct.textContent = `${confPct}%`;
  confidenceBar.setAttribute("aria-valuenow", confPct);
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      confidenceFill.style.width = `${confPct}%`;
    });
  });

  methodNote.textContent = result.methodology;

  // Breakdown
  renderBreakdown(result.category_results);
  showSection(breakdownSection);

  // Actions
  renderActions(result.personalized_actions);
  showSection(actionsSection);

  // Insights
  renderInsights(result.insights);
  showSection(insightsSection);

  // Context comparison
  renderContext(result.total_yearly_tonnes);
  showSection(contextSection);
}

// ── Form submit ──────────────────────────────────────────────
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  setStatus("Calculating your footprint…");

  const formData = new FormData(form);
  let payload;

  try {
    payload = buildPayload(formData);
  } catch (validationError) {
    setStatus(validationError.message, "error");
    submitBtn.disabled = false;
    return;
  }

  try {
    const response = await fetch("/api/footprint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let detail = `Request failed (${response.status}).`;
      try {
        const errBody = await response.json();
        if (errBody.detail) {
          detail = Array.isArray(errBody.detail)
            ? errBody.detail.map(d => d.msg || JSON.stringify(d)).join("; ")
            : String(errBody.detail);
        }
      } catch (_) { /* ignore */ }
      throw new Error(detail);
    }

    const result = await response.json();
    renderResult(result);
    setStatus("✓ Results updated with personalised recommendations.", "success");

    // Scroll results into view on mobile
    if (window.innerWidth <= 1000) {
      document.getElementById("results-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (error) {
    setStatus(`Could not calculate right now: ${error.message}`, "error");
    console.error("Footprint API error:", error);
  } finally {
    submitBtn.disabled = false;
  }
});
