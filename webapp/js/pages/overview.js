/* Overview — business at a glance. Real data only. */

import { api } from "../api.js";
import {
  decisionChip,
  el,
  emptyState,
  esc,
  eventBadge,
  fmt,
  icon,
  orderStatusBadge,
  paymentStateBadge,
  qs,
  skeleton,
} from "../ui.js";
import { areaChart, sparkline } from "../charts.js";

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="overview-kpis" id="kpis">${skeleton.kpis(4)}</div>
    <div id="attention"></div>
    <div class="overview-grid">
      <div class="card">
        <div class="card__head">
          <div><h2>Revenue</h2><div class="sub">Last 7 days, delivered and in-flight orders</div></div>
          <div class="segmented" id="range-note"><button class="is-active" disabled>7 days</button></div>
        </div>
        <div class="card__body"><div class="chart" id="revenue-chart">${skeleton.chart(210)}</div></div>
      </div>
      <div class="card">
        <div class="card__head"><div><h2>Orders by status</h2><div class="sub">All time</div></div></div>
        <div class="card__body" id="status-bars"><div class="skel skel--chart" style="height:150px"></div></div>
      </div>
    </div>
    <div class="overview-grid">
      <div class="card card--flush">
        <div class="card__head">
          <div><h2>Recent orders</h2><div class="sub">Newest first</div></div>
          <a class="btn btn--sm" href="#/orders">View all ${icon("chevronRight", 14)}</a>
        </div>
        <div id="recent-orders">${skeleton.table(4)}</div>
      </div>
      <div class="card card--flush">
        <div class="card__head">
          <div><h2>Payment activity</h2><div class="sub">Latest detected transactions</div></div>
          <a class="btn btn--sm" href="#/payments">Reconcile ${icon("chevronRight", 14)}</a>
        </div>
        <div id="recent-events">${skeleton.table(4)}</div>
      </div>
    </div>`;

  const [summary, intelligence, orders, events] = await Promise.all([
    api.summary(ctx.businessId),
    api.intelligenceSummary(ctx.businessId),
    api.orders(ctx.businessId),
    api.intelligenceEvents(ctx.businessId, { limit: 6, sort: "newest" }),
  ]);

  renderKpis(summary, intelligence, ctx);
  renderAttention(intelligence, root);
  renderChart(summary.daily, root);
  renderStatusBars(summary.orders_by_status, root);
  renderRecentOrders(orders, ctx, root);
  renderRecentEvents(events.items || [], ctx, root);
}

function renderKpis(summary, intelligence, ctx) {
  const kpis = el(`<div class="overview-kpis"></div>`);
  const dailyRevenue = (summary.daily || []).map((point) => Number(point.revenue));
  const totalOrders = Number(summary.total_orders || 0);
  const verifiedTotal = Number(intelligence.verified_amount_total || 0);

  const items = [
    {
      label: "Total revenue",
      value: fmt.money(summary.total_revenue),
      foot: `<span>Today ${fmt.money(summary.today_revenue)}</span>`,
      spark: dailyRevenue,
    },
    {
      label: "Gross profit",
      value: fmt.money(summary.total_profit),
      foot: `<span>Today ${fmt.money(summary.today_profit)}</span>`,
      spark: (summary.daily || []).map((point) => Number(point.profit)),
    },
    {
      label: "Orders",
      value: fmt.num(totalOrders),
      foot: `<span>${fmt.num(summary.today_orders)} today</span>`,
    },
    {
      label: "Verified payments",
      value: fmt.money(verifiedTotal),
      hero: true,
      foot: `<span>${fmt.num(intelligence.paid_events)} matched · ${fmt.num(intelligence.review_events)} to review</span>`,
    },
  ];

  kpis.innerHTML = items
    .map(
      (item) => `
    <div class="card kpi ${item.hero ? "kpi--hero" : ""}">
      <div class="kpi__label">${esc(item.label)}</div>
      <div class="kpi__value">${esc(item.value)}</div>
      <div class="kpi__foot">${item.foot}</div>
      ${item.spark && item.spark.some((v) => v) ? `<div class="kpi__spark">${sparkline(item.spark, item.hero ? { stroke: "#2ED3C0" } : {})}</div>` : ""}
    </div>`
    )
    .join("");

  qs("#kpis").replaceWith(kpis);
  kpis.id = "kpis";
  kpis.classList.add("page-enter");
}

function renderAttention(intelligence, root) {
  const review = Number(intelligence.review_events || 0);
  if (!review) return;
  qs("#attention", root).innerHTML = `
    <div class="attention">
      ${icon("alert", 17)}
      <span>${esc(fmt.num(review))} payment${review === 1 ? "" : "s"} need${review === 1 ? "s" : ""} review — no confident order match yet.</span>
      <a href="#/payments?status=review" class="right">Review now</a>
    </div>`;
}

function renderChart(daily, root) {
  const points = (daily || []).map((point) => ({
    label: new Date(`${point.date}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short" }),
    value: Number(point.revenue),
  }));
  areaChart(qs("#revenue-chart", root), {
    data: points,
    format: (value) => fmt.money(value, { decimals: true }),
  });
}

function renderStatusBars(byStatus, root) {
  const order = ["created", "confirmed", "packed", "shipped", "delivered", "cancelled"];
  const entries = order
    .map((key) => [key, Number((byStatus || {})[key] || 0)])
    .filter(([key, value]) => value > 0 || key === "created");
  const max = Math.max(...entries.map(([, value]) => value), 1);
  if (!entries.length) {
    qs("#status-bars", root).innerHTML = emptyState({ iconName: "receipt", title: "No orders yet", message: "Create your first order to see the pipeline." });
    return;
  }
  qs("#status-bars", root).innerHTML = `
    <div class="bar-list">
      ${entries
        .map(
          ([key, value]) => `
        <div class="rowline">
          <span class="name">${esc(key)}</span>
          <div class="track"><div class="fill" style="width:${Math.round((value / max) * 100)}%; ${key === "cancelled" ? "background:var(--danger)" : ""}"></div></div>
          <span class="value">${fmt.num(value)}</span>
        </div>`
        )
        .join("")}
    </div>`;
}

function renderRecentOrders(orders, ctx, root) {
  const rows = (orders || []).slice(0, 5);
  if (!rows.length) {
    qs("#recent-orders", root).innerHTML = emptyState({
      iconName: "receipt",
      title: "No orders yet",
      message: "Orders you create will show up here.",
      action: `<a class="btn btn--primary btn--sm" href="#/orders">${icon("plus", 14)} New order</a>`,
    });
    return;
  }
  qs("#recent-orders", root).innerHTML = `
    <div class="table-wrap">
      <table class="table table--cards">
        <thead><tr><th>Order</th><th>Customer</th><th class="num">Total</th><th>Payment</th><th>Status</th></tr></thead>
        <tbody>
          ${rows
            .map(
              (order) => `
            <tr>
              <td class="cell-lead" data-label="Order"><span class="cell-title">#${order.id}</span><span class="cell-sub">${esc(fmt.relative(order.created_at))}</span></td>
              <td data-label="Customer">${esc(order.customer?.name || "Walk-in")}</td>
              <td class="num" data-label="Total">${esc(fmt.money(order.total_amount, { decimals: true }))}</td>
              <td data-label="Payment">${paymentStateBadge(order.payment_status)}</td>
              <td data-label="Status">${orderStatusBadge(order.status)}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
}

function renderRecentEvents(events, ctx, root) {
  if (!events.length) {
    qs("#recent-events", root).innerHTML = emptyState({
      iconName: "wallet",
      title: "No payments detected yet",
      message: "Connect the payment bridge or record payments manually.",
    });
    return;
  }
  qs("#recent-events", root).innerHTML = `
    <div class="recent-list">
      ${events
        .map(
          (event) => `
        <div class="recent-item">
          <span class="thumb">${icon(event.source_type === "sms" ? "phone" : "fileText", 16)}</span>
          <div class="main-col">
            <div class="t">${esc(fmt.money(event.amount, { decimals: true }))} <span class="dim" style="font-weight:500">· ${esc(event.provider)}</span></div>
            <div class="s mono">${esc(event.transaction_id)}</div>
          </div>
          <div style="text-align:right">
            ${eventBadge(event)}
            <div class="s" style="font-size:var(--fs-11); color:var(--text-3); margin-top:3px">${esc(fmt.relative(event.event_timestamp))}</div>
          </div>
        </div>`
        )
        .join("")}
    </div>`;
}
