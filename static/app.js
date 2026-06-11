const form = document.querySelector("#footprint-form");
const statusEl = document.querySelector("#form-status");
const monthlyTotal = document.querySelector("#monthly-total");
const yearlyTotal = document.querySelector("#yearly-total");
const breakdown = document.querySelector("#breakdown");
const actions = document.querySelector("#actions");
const insights = document.querySelector("#insights");

function numberValue(formData, key) {
  return Number(formData.get(key) || 0);
}

function card(title, meta, body) {
  const el = document.createElement("article");
  el.className = "card";
  el.innerHTML = `<strong></strong><p class="meta"></p><p></p>`;
  el.querySelector("strong").textContent = title;
  el.querySelector(".meta").textContent = meta;
  el.querySelector("p:last-child").textContent = body;
  return el;
}

function renderResult(result) {
  monthlyTotal.textContent = result.total_monthly_kg.toLocaleString();
  yearlyTotal.textContent = `${result.total_yearly_tonnes} tonnes CO2e/year • confidence ${Math.round(result.confidence_score * 100)}%`;

  breakdown.replaceChildren(
    ...result.category_results.map((item) =>
      card(item.category, `${item.monthly_kg} kg/month`, item.explanation)
    )
  );

  actions.replaceChildren(
    ...result.personalized_actions.map((item) =>
      card(item.title, `${item.impact_kg_month} kg/month saving • ${item.effort} effort`, item.why_it_matters)
    )
  );

  insights.replaceChildren(
    ...result.insights.map((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      return li;
    })
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Calculating your footprint...";

  const formData = new FormData(form);
  const payload = {
    profile: {
      name: String(formData.get("name") || "Friend"),
      country: String(formData.get("country") || "India"),
      goal: String(formData.get("goal") || "reduce_emissions"),
    },
    home: {
      electricity_kwh: numberValue(formData, "electricity_kwh"),
      natural_gas_therms: numberValue(formData, "natural_gas_therms"),
      renewable_percent: numberValue(formData, "renewable_percent"),
      household_size: numberValue(formData, "household_size"),
    },
    transport: [
      {
        mode: String(formData.get("transport_mode") || "bus"),
        km_per_week: numberValue(formData, "km_per_week"),
      },
    ],
    lifestyle: {
      diet: String(formData.get("diet") || "mixed"),
      meals_out_per_week: numberValue(formData, "meals_out_per_week"),
      new_items_per_month: numberValue(formData, "new_items_per_month"),
      waste_bags_per_week: numberValue(formData, "waste_bags_per_week"),
    },
  };

  try {
    const response = await fetch("/api/footprint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    renderResult(await response.json());
    statusEl.textContent = "Updated with personalized recommendations.";
  } catch (error) {
    statusEl.textContent = "Could not calculate right now. Check the server and try again.";
  }
});
