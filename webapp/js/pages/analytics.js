/* Analytics — real aggregation views only (no invented figures). */

import { api } from "../api.js";
import { emptyState, esc, fmt, icon, qs, skeleton } from "../ui.js";
import { areaChart, donutChart } from "../charts.js";

let metric = "revenue";

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="grid grid-4" id="an-kpis">${skeleton.kpis(4)}</div>
    <div class="card">
      <div class="card__head">
        <div><h3 id="chart-title">Revenue</h2><div class="sub">Last 7 days · from recorded orders</div></div>
        <div class="segmented" id="metric-switch">
          <button data-metric="revenue" class="is-active">Revenue</button>
          <button data-metric="profit">Profit</button>
        </div>
      </div>
      <div class="card__body"><div class="chart" id="trend-chart">${skeleton.chart(240)}</div></div>
    </div>
    <div class="overview-grid">
      <div class="card">
        <div class="card__head"><div><h2>Orders by status</h2><div class="sub">All orders, including cancelled</div></div></div>
        <div class="card__body" id="status-bars">${skeleton.chart(150)}</div>
      </div>
      <div class="card">
        <div class="card__head"><div><h2>Payment health</h2><div class="sub">Detected transactions by outcome</div></div></div>
        <div class="card__body" id="payment-health">${skeleton.chart(170)}</div>
      </div>
    </div>
    <p class="small dim" style="margin-top:-6px">${icon("info", 12)} Cancelled orders are excluded from revenue and profit — they stay visible in the status breakdown.</p>`;

  const [summary, intelligence] = await Promise.all([
    api.summary(ctx.businessId),
    api.intelligenceSummary(ctx.businessId),
  ]);

  renderKpis(summary, intelligence);
  renderTrend(summary);
  renderStatus(root, summary);
  renderHealth(root, intelligence);

  qs("#metric-switch", root).addEventListener("click", (event) => {
    const button = event.target.closest("[data-metric]");
    if (!button) return;
    metric = button.dataset.metric;
    qs("#metric-switch .is-active")?.classList.remove("is-active");
    button.classList.add("is-active");
    qs("#chart-title", root).textContent = metric === "revenue" ? "Revenue" : "Gross profit";
    renderTrend(summary);
  });
}

function renderKpis(summary, intelligence) {
  const orders = Number(summary.total_orders || 0);
  const revenue = Number(summary.total_revenue || 0);
  const averageOrder = orders > 0 ? revenue / orders : 0;
  qs("#an-kpis").innerHTML = [
    ["Total revenue", fmt.money(revenue), "Cancelled orders excluded"],
    ["Gross profit", fmt.money(summary.total_profit), "Revenue minus product cost"],
    ["Average order value", fmt.money(averageOrder), `${fmt.num(orders)} orders recorded`],
    ["Pending deliveries", fmt.num(summary.pending_deliveries), `${fmt.num(intelligence.total_events)} payments detected`],
  ]
    .map(
      ([label, value, sub]) => `
      <div class="card kpi">
        <div class="kpi__label">${esc(label)}</div>
        <div class="kpi__value">${esc(value)}</div>
        <div class="kpi__foot">${esc(sub)}</div>
      </div>`
    )
    .join("");
}

function renderTrend(summary) {
  const points = (summary.daily || []).map((point) => ({
    label: new Date(`${point.date}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short" }),
    value: Number(metric === "revenue" ? point.revenue : point.profit),
  }));
  areaChart(qs("#trend-chart"), {
    data: points,
    height: 240,
    format: (value) => fmt.money(value, { decimals: true }),
  });
}

function renderStatus(root, summary) {
  const order = ["created", "confirmed", "packed", "shipped", "delivered", "cancelled"];
  const entries = order.map((key) => [key, Number(summary.orders_by_status?.[key] || 0)]);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  const any = entries.some(([, value]) => value > 0);
  qs("#status-bars", root).innerHTML = any
    ? `<div class="bar-list">
        ${entries
          .filter(([, value]) => value > 0)
          .map(
            ([key, value]) => `
          <div class="rowline">
            <span class="name">${esc(key)}</span>
            <div class="track"><div class="fill" style="width:${Math.round((value / max) * 100)}%; ${key === "cancelled" ? "background:var(--danger)" : ""}"></div></div>
            <span class="value">${fmt.num(value)}</span>
          </div>`
          )
          .join("")}
      </div>`
    : emptyState({ iconName: "receipt", title: "No orders yet", message: "Status breakdown appears once orders exist." });
}

function renderHealth(root, intelligence) {
  const segments = [
    { label: "Verified", value: Number(intelligence.paid_events || 0), color: "#0E988C" },
    { label: "In review", value: Number(intelligence.review_events || 0), color: "#D99B1E" },
    { label: "Partial", value: Number(intelligence.partial_events || 0), color: "#2563EB" },
    { label: "Duplicate", value: Number(intelligence.duplicate_events || 0), color: "#8A98AE" },
  ];
  donutChart(qs("#payment-health", root), {
    segments,
    centerValue: fmt.num(intelligence.total_events || 0),
    centerLabel: "events",
  });
}
