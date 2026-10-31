/* Payments — reconciliation: detected transactions, recorded payments, accounts. */

import { api } from "../api.js";
import {
  clearFieldErrors,
  copyText,
  decisionChip,
  emptyState,
  esc,
  eventBadge,
  fieldError,
  fmt,
  formValues,
  icon,
  on,
  openModal,
  providerLabel,
  qs,
  qsa,
  recordedPaymentBadge,
  setBusy,
  skeleton,
  toast,
} from "../ui.js";

const PAGE_SIZE = 25;

const state = {
  tab: "transactions",
  events: [],
  total: 0,
  offset: 0,
  search: "",
  status: "",
  provider: "",
  summary: null,
  payments: [],
  accounts: [],
};

export async function render(root, ctx) {
  state.tab = ctx.query.tab || "transactions";
  if (ctx.query.status) state.status = ctx.query.status;
  paint(root);

  qs("#pmt-tabs", root).addEventListener("click", (event) => {
    const tab = event.target.closest("[data-tab]");
    if (!tab) return;
    state.tab = tab.dataset.tab;
    window.location.hash = `#/payments?tab=${state.tab}`;
    paint(root);
  });

  await load(root, ctx);
}

function paint(root) {
  const tabs = [
    ["transactions", "Transactions", state.summary?.total_events],
    ["recorded", "Recorded payments", state.payments.length || null],
    ["accounts", "Accounts", state.accounts.length || null],
  ];
  root.innerHTML = `
    <div class="toolbar">
      <div class="tabs" id="pmt-tabs">
        ${tabs
          .map(
            ([key, label, count]) => `
          <button class="tab ${state.tab === key ? "is-active" : ""}" data-tab="${key}">
            ${esc(label)}${count ? `<span class="count">${fmt.num(count)}</span>` : ""}
          </button>`
          )
          .join("")}
      </div>
      <button class="btn btn--sm js-refresh-${state.tab}">${icon("refresh", 14)} Refresh</button>
    </div>
    <div id="pmt-content">${skeleton.table(6)}</div>`;
  on(root, "click", ".js-refresh-transactions", () => load(root, ctx));
  on(root, "click", ".js-refresh-recorded", () => load(root, ctx));
  on(root, "click", ".js-refresh-accounts", () => load(root, ctx));
}

async function load(root, ctx) {
  try {
    if (state.tab === "transactions") await loadTransactions(root, ctx);
    else if (state.tab === "recorded") await loadRecorded(root, ctx);
    else await loadAccounts(root, ctx);
  } catch (error) {
    qs("#pmt-content", root).innerHTML = `<div class="card">${emptyState({
      iconName: "alert",
      title: "Could not load payments",
      message: error.message,
    })}</div>`;
  }
}

/* ------------------------------------------------------------ transactions */

async function loadTransactions(root, ctx) {
  const params = {
    limit: PAGE_SIZE,
    offset: state.offset,
    sort: "newest",
  };
  if (state.search) params.search = state.search;
  if (state.status) params.status = state.status;
  if (state.provider) params.provider = state.provider;

  const [summary, page] = await Promise.all([
    api.intelligenceSummary(ctx.businessId),
    api.intelligenceEvents(ctx.businessId, params),
  ]);
  state.summary = summary;
  state.events = page.items || [];
  state.total = page.total_count || 0;

  const host = qs("#pmt-content", root);
  host.innerHTML = `
    <div class="grid grid-4" style="margin-top:2px">
      ${statCard("Verified amount", fmt.money(summary.verified_amount_total), `${fmt.money(summary.verified_amount_today)} today`, "wallet")}
      ${statCard("Matched payments", fmt.num(summary.paid_events), "Confidently linked to orders", "checkCircle")}
      ${statCard("Needs review", fmt.num(summary.review_events), "No confident order match", "alert")}
      ${statCard("Duplicates", fmt.num(summary.duplicate_events), "Replayed transactions blocked", "shield")}
    </div>
    <div class="card card--flush">
      <div class="card__head">
        <div class="filters-bar grow">
          <div class="input-group search-wide">
            ${icon("search", 16)}
            <input class="input" id="ev-search" aria-label="Search transactions" placeholder="Search TrxID or sender…" value="${esc(state.search)}">
          </div>
          <select class="select" id="ev-status" aria-label="Filter by status" style="width:auto">
            ${selectOptions(
              ["", "verified", "review", "pending_verification", "partial", "duplicate"],
              state.status,
              { "": "All statuses", verified: "Verified", review: "Needs review", pending_verification: "Pending", partial: "Partial", duplicate: "Duplicate" }
            )}
          </select>
          <select class="select" id="ev-provider" aria-label="Filter by provider" style="width:auto">
            ${selectOptions(["", "bkash", "nagad", "rocket", "upay"], state.provider, { "": "All providers", bkash: "bKash", nagad: "Nagad", rocket: "Rocket", upay: "Upay" })}
          </select>
        </div>
      </div>
      <div id="ev-table">${paintEventTable()}</div>
      <div class="pagination">
        <span class="small dim">${state.total ? `Showing ${state.offset + 1}–${state.offset + state.events.length} of ${fmt.num(state.total)}` : "No transactions"}</span>
        <button class="btn btn--sm js-prev" ${state.offset === 0 ? "disabled" : ""}>${icon("chevronLeft", 14)} Previous</button>
        <button class="btn btn--sm js-next" ${state.offset + PAGE_SIZE >= state.total ? "disabled" : ""}>Next ${icon("chevronRight", 14)}</button>
      </div>
    </div>`;

  const searchInput = qs("#ev-search", host);
  let searchTimer;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.search = searchInput.value.trim();
      state.offset = 0;
      loadTransactions(root, ctx);
    }, 260);
  });
  qs("#ev-status", host).addEventListener("change", (event) => {
    state.status = event.target.value;
    state.offset = 0;
    loadTransactions(root, ctx);
  });
  qs("#ev-provider", host).addEventListener("change", (event) => {
    state.provider = event.target.value;
    state.offset = 0;
    loadTransactions(root, ctx);
  });
  qs(".js-prev", host).addEventListener("click", () => {
    state.offset = Math.max(0, state.offset - PAGE_SIZE);
    loadTransactions(root, ctx);
  });
  qs(".js-next", host).addEventListener("click", () => {
    state.offset += PAGE_SIZE;
    loadTransactions(root, ctx);
  });
  on(qs("#ev-table", host), "click", ".js-event-row", (event, target) => {
    const id = Number(target.dataset.id);
    const item = state.events.find((row) => row.event_id === id);
    if (item) openEventDetail(item, root, ctx);
  });
}

function paintEventTable() {
  if (!state.events.length) {
    return emptyState({
      iconName: "wallet",
      title: "No transactions found",
      message: state.search || state.status || state.provider
        ? "Try clearing the filters."
        : "Detected payments will appear here once the payment bridge reports them.",
    });
  }
  return `
    <div class="table-wrap">
      <table class="table table--cards">
        <thead>
          <tr><th>Transaction</th><th class="num">Amount</th><th>Sender</th><th>Order</th><th>Confidence</th><th>Status</th><th>Received</th><th><span class="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          ${state.events
            .map(
              (event) => `
            <tr>
              <td class="cell-lead" data-label="Transaction">
                <div class="event-tx">
                  <span class="id">${esc(event.transaction_id)}</span>
                  <span class="cell-sub">${esc(event.provider)} · via ${esc(event.source_type === "sms" ? "SMS bridge" : event.source_type)}</span>
                </div>
              </td>
              <td class="num" data-label="Amount"><b>${esc(fmt.money(event.amount, { decimals: true }))}</b></td>
              <td data-label="Sender">${event.sender_identifier ? `<span class="mono small">${esc(event.sender_identifier)}</span>` : `<span class="dim">not in SMS</span>`}</td>
              <td data-label="Order">${event.order_id ? `<a href="#/orders" class="small">#${event.order_id}</a>` : `<span class="dim">—</span>`}</td>
              <td data-label="Confidence">${confidenceBar(event)}</td>
              <td data-label="Status">${eventBadge(event)}</td>
              <td data-label="Received"><span class="small dim">${esc(fmt.relative(event.event_timestamp))}</span></td>
              <td data-label=""><button class="btn btn--sm js-event-row" data-id="${event.event_id}">Details</button></td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
}

function confidenceBar(event) {
  const value = Math.round((Number(event.confidence) || 0) * 100);
  return `
    <span class="confidence" title="Engine confidence ${value}%">
      <span class="bar"><i style="width:${value}%; ${value < 50 ? "background:var(--warn)" : ""}"></i></span>
      ${value}%
    </span>`;
}

function openEventDetail(event, root, ctx) {
  openModal({
    title: `Transaction ${event.transaction_id}`,
    body: `
      <div class="stack">
        <div class="row-tight">${eventBadge(event)} ${decisionChip(event)}</div>
        <div class="grid grid-2" style="gap:var(--sp-4)">
          ${detailRow("Amount", fmt.money(event.amount, { decimals: true }))}
          ${detailRow("Provider", providerLabel(event.provider))}
          ${detailRow("Sender", event.sender_identifier || "Not present in the SMS")}
          ${detailRow("Receiving number", event.receiver_identifier || "—")}
          ${detailRow("Source", event.source_type === "sms" ? "SMS bridge (device)" : fmt.titleCase(event.source_type))}
          ${detailRow("Matched order", event.order_id ? `#${event.order_id}` : "No order match")}
          ${detailRow("Confidence", `${Math.round((Number(event.confidence) || 0) * 100)}%`)}
          ${detailRow("Received", fmt.dateTime(event.event_timestamp))}
        </div>
        ${event.explanation ? `<div class="pill-note" style="align-items:flex-start">${icon("info", 15)}<span>${esc(event.explanation)}</span></div>` : ""}
        ${event.reason_codes?.length ? `<div class="tag-list">${event.reason_codes.map((code) => `<span class="reason-tag">${esc(code)}</span>`).join("")}</div>` : ""}
        ${
          event.order_id
            ? `<a class="btn btn--sm" href="#/orders">${icon("receipt", 14)} Open orders</a>`
            : `<div class="pill-note">${icon("alert", 14)} This payment needs a human decision. Record it manually from the order, or wait for a stronger signal.</div>`
        }
      </div>`,
    footer: `<button class="btn" data-close-modal>Close</button>`,
  });
}

function detailRow(label, value) {
  return `<div><div class="small dim">${esc(label)}</div><div style="font-weight:600; color:var(--ink)">${esc(value)}</div></div>`;
}

function statCard(label, value, sub, iconName) {
  return `
    <div class="card kpi" style="padding:var(--sp-4) var(--sp-5)">
      <div class="kpi__label">${icon(iconName, 14)} ${esc(label)}</div>
      <div class="kpi__value" style="font-size:var(--fs-23)">${esc(value)}</div>
      <div class="kpi__foot">${esc(sub)}</div>
    </div>`;
}

/* ----------------------------------------------------------- recorded list */

async function loadRecorded(root, ctx) {
  state.payments = await api.payments(ctx.businessId);
  const host = qs("#pmt-content", root);
  if (!state.payments.length) {
    host.innerHTML = `<div class="card">${emptyState({
      iconName: "wallet",
      title: "No recorded payments",
      message: "Record a payment from an order and it will appear here.",
      action: `<a class="btn btn--primary btn--sm" href="#/orders">${icon("receipt", 14)} Go to orders</a>`,
    })}</div>`;
    return;
  }
  host.innerHTML = `
    <div class="card card--flush">
      <div class="table-wrap">
        <table class="table table--cards">
          <thead><tr><th>Paid</th><th>Order</th><th>Method</th><th class="num">Amount</th><th>Reference</th><th>Status</th></tr></thead>
          <tbody>
            ${state.payments
              .map(
                (payment) => `
              <tr>
                <td class="cell-lead" data-label="Paid"><span class="cell-title">${esc(fmt.dateTime(payment.paid_at || payment.created_at))}</span></td>
                <td data-label="Order"><a href="#/orders">#${payment.order_id}</a></td>
                <td data-label="Method">${providerChip(payment.method)}</td>
                <td class="num" data-label="Amount"><b>${esc(fmt.money(payment.amount, { decimals: true }))}</b></td>
                <td data-label="Reference">${
                  payment.transaction_id
                    ? `<span class="mono small">${esc(payment.transaction_id)}</span>
                       <button class="copy-btn js-copy" data-copy="${esc(payment.transaction_id)}" aria-label="Copy reference">${icon("copy", 13)}</button>`
                    : `<span class="dim small">—</span>`
                }</td>
                <td data-label="Status">${recordedPaymentBadge(payment.status)}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>`;
  on(host, "click", ".js-copy", (event, target) => copyText(target.dataset.copy));
}

/* ---------------------------------------------------------------- accounts */

async function loadAccounts(root, ctx) {
  state.accounts = await api.paymentAccounts(ctx.businessId);
  const host = qs("#pmt-content", root);
  host.innerHTML = `
    <div class="overview-grid">
      <div class="card card--flush">
        <div class="card__head"><div><h2>Connected accounts</h2><div class="sub">Where your customers send money</div></div></div>
        <div class="card__body">
          ${
            state.accounts.length
              ? state.accounts
                  .map(
                    (account) => `
              <div class="provider-row">
                <span class="provider-logo">${providerLogo(account.provider)}</span>
                <div class="grow">
                  <div style="font-weight:600; color:var(--ink)">${esc(providerLabel(account.provider))} · <span class="mono">${esc(account.receiving_number)}</span></div>
                  <div class="small dim">Connected ${esc(fmt.date(account.connected_at))}</div>
                </div>
                <span class="badge badge--ok">${esc(account.status)}</span>
                <button class="copy-btn js-copy" data-copy="${esc(account.receiving_number)}" aria-label="Copy number">${icon("copy", 14)}</button>
              </div>`
                  )
                  .join("")
              : emptyState({ iconName: "bank", title: "No accounts connected", message: "Connect the number your customers pay into." })
          }
        </div>
      </div>
      <div class="card">
        <div class="card__head"><div><h2>Connect a number</h2><div class="sub">Used to match incoming payments</div></div></div>
        <div class="card__body">
          <form id="account-form" novalidate class="stack">
            <div class="field">
              <label for="acc-provider">Provider</label>
              <select class="select" id="acc-provider" name="provider">
                ${selectOptions(["bkash", "nagad", "rocket", "upay"], "bkash", { bkash: "bKash", nagad: "Nagad", rocket: "Rocket", upay: "Upay" })}
              </select>
            </div>
            <div class="field">
              <label for="acc-number">Receiving number</label>
              <input class="input" id="acc-number" name="receiving_number" inputmode="tel" placeholder="01XXXXXXXXX">
              <span class="hint">Must be the number your customers actually pay into.</span>
            </div>
            <button class="btn btn--primary" type="submit">${icon("link", 15)} Connect account</button>
          </form>
          <div class="pill-note" style="margin-top:16px; align-items:flex-start">${icon("info", 14)}<span>The Android payment bridge reports SMS payments for the number connected here.</span></div>
        </div>
      </div>
    </div>`;

  on(host, "click", ".js-copy", (event, target) => copyText(target.dataset.copy));
  qs("#account-form", host).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    clearFieldErrors(form);
    const values = formValues(form);
    if (!values.receiving_number) {
      fieldError(form, "receiving_number", "Enter the receiving number");
      return;
    }
    const button = qs('button[type="submit"]', form);
    setBusy(button, true, "Connecting…");
    try {
      await api.connectPaymentAccount(ctx.businessId, {
        provider: values.provider,
        receiving_number: values.receiving_number,
      });
      toast("Payment account connected", { title: "Account saved" });
      await loadAccounts(root, ctx);
    } catch (error) {
      setBusy(button, false);
      toast(error.message || "Could not connect the account", { type: "error" });
    }
  });
}

/* ----------------------------------------------------------------- helpers */

function selectOptions(values, selected, labels) {
  return values
    .map(
      (value) =>
        `<option value="${esc(value)}" ${value === selected ? "selected" : ""}>${esc(labels?.[value] ?? fmt.titleCase(value || "All"))}</option>`
    )
    .join("");
}

export function providerLogo(provider) {
  const known = { bkash: "bkash", nagad: "nagad", paypal: "paypal", cashapp: "cashapp", stripe: "stripe" };
  if (known[provider]) {
    return `<img src="/assets/images/${known[provider]}.svg" alt="" loading="lazy">`;
  }
  return icon("wallet", 18);
}

function providerChip(method) {
  return `<span class="row-tight">${providerLogo(method)}<span>${esc(providerLabel(method))}</span></span>`;
}
