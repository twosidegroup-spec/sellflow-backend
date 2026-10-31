/* Customers — directory with real purchase summaries, a per-customer detail
   view backed by their actual order history, and a non-blocking duplicate
   phone warning on create/edit. */

import { api } from "../api.js";
import {
  clearFieldErrors,
  confirmDialog,
  emptyState,
  esc,
  fieldError,
  fmt,
  formValues,
  icon,
  on,
  openModal,
  orderStatusBadge,
  paymentStateBadge,
  qs,
  setBusy,
  skeleton,
  toast,
} from "../ui.js";

let state = { customers: [], orders: [], search: "", loading: false };

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="toolbar">
      <div class="input-group grow" style="min-width:min(300px,100%)">
        ${icon("search", 16)}
        <input class="input" id="customer-search" aria-label="Search customers" placeholder="Search by name, phone or email…" value="${esc(state.search)}">
      </div>
      <div class="row-tight">
        <button class="btn js-refresh">${icon("refresh", 15)} Refresh</button>
        <button class="btn btn--primary js-new-customer">${icon("plus", 16)} New customer</button>
      </div>
    </div>
    <div class="card card--flush"><div id="customers-table">${skeleton.table(6)}</div></div>`;

  on(root, "click", ".js-refresh", () => render(root, ctx));
  on(root, "click", ".js-new-customer", () => openCustomerForm(root, ctx, null));
  qs("#customer-search", root).addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    paint(root, ctx);
  });

  [state.customers, state.orders] = await Promise.all([
    api.customers(ctx.businessId),
    api.orders(ctx.businessId),
  ]);
  paint(root, ctx);
}

/* Purchase summaries come from the real order records. Cancelled orders are
   counted separately and never included in money totals. */
function summaries() {
  const map = new Map();
  for (const order of state.orders) {
    if (!order.customer_id) continue;
    const entry = map.get(order.customer_id) || { count: 0, spent: 0, cancelled: 0, lastAt: null };
    if (order.status === "cancelled") {
      entry.cancelled += 1;
    } else {
      entry.count += 1;
      entry.spent += Number(order.total_amount || 0);
      if (!entry.lastAt || new Date(order.created_at) > new Date(entry.lastAt)) {
        entry.lastAt = order.created_at;
      }
    }
    map.set(order.customer_id, entry);
  }
  return map;
}

function filtered() {
  if (!state.search) return state.customers;
  return state.customers.filter((customer) => {
    const haystack = `${customer.name} ${customer.phone || ""} ${customer.email || ""}`.toLowerCase();
    return haystack.includes(state.search);
  });
}

function paint(root, ctx) {
  const host = qs("#customers-table", root);
  const rows = filtered();
  const stats = summaries();
  if (!state.customers.length) {
    host.innerHTML = emptyState({
      iconName: "users",
      title: "No customers yet",
      message: "Add a customer or create an order to start your directory.",
      action: `<button class="btn btn--primary btn--sm js-new-customer">${icon("plus", 14)} New customer</button>`,
    });
    on(host, "click", ".js-new-customer", () => openCustomerForm(root, ctx, null));
    return;
  }
  if (!rows.length) {
    host.innerHTML = emptyState({ iconName: "search", title: "No matching customers", message: "Try a different search term." });
    return;
  }

  host.innerHTML = `
    <div class="table-wrap">
      <table class="table table--cards">
        <thead>
          <tr>
            <th>Customer</th><th class="num">Orders</th><th class="num">Purchased</th>
            <th>Last order</th><th>Added</th><th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((customer) => {
              const stat = stats.get(customer.id) || { count: 0, spent: 0, lastAt: null };
              return `
            <tr data-id="${customer.id}">
              <td class="cell-lead" data-label="Customer">
                <div class="row-tight">
                  <span class="avatar">${esc(fmt.initials(customer.name))}</span>
                  <div>
                    <div class="cell-title">${esc(customer.name)}</div>
                    <div class="cell-sub">${customer.phone ? `<span class="mono">${esc(customer.phone)}</span>` : "No phone on file"}</div>
                  </div>
                </div>
              </td>
              <td class="num" data-label="Orders">${stat.count ? fmt.num(stat.count) : `<span class="dim">0</span>`}</td>
              <td class="num" data-label="Purchased">${stat.count ? esc(fmt.money(stat.spent)) : `<span class="dim">—</span>`}</td>
              <td data-label="Last order">${stat.lastAt ? `<span class="small">${esc(fmt.relative(stat.lastAt))}</span>` : `<span class="dim">Never</span>`}</td>
              <td data-label="Added"><span class="small dim">${esc(fmt.date(customer.created_at))}</span></td>
              <td data-label="Actions">
                <div class="row-actions">
                  <button class="icon-btn js-view" title="View profile" aria-label="View ${esc(customer.name)}">${icon("eye", 15)}</button>
                  <button class="icon-btn js-edit" aria-label="Edit ${esc(customer.name)}">${icon("edit", 15)}</button>
                  <button class="icon-btn js-delete" aria-label="Delete ${esc(customer.name)}">${icon("trash", 15)}</button>
                </div>
              </td>
            </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>`;

  on(host, "click", ".js-view", (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    openCustomerDetail(root, ctx, id);
  });
  on(host, "click", ".js-edit", (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    openCustomerForm(root, ctx, state.customers.find((customer) => customer.id === id));
  });
  on(host, "click", ".js-delete", async (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    const customer = state.customers.find((item) => item.id === id);
    const stat = summaries().get(id);
    const confirmed = await confirmDialog({
      title: "Delete customer?",
      message:
        `“${customer.name}” will be removed from your directory. ` +
        (stat?.count
          ? `Their ${stat.count} order${stat.count === 1 ? "" : "s"} stay in your records but will no longer be linked to a profile.`
          : "Orders keep their history."),
      confirmText: "Delete customer",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await api.deleteCustomer(ctx.businessId, id);
      toast("Customer deleted");
      state.customers = state.customers.filter((item) => item.id !== id);
      paint(root, ctx);
    } catch (error) {
      toast(error.message || "Could not delete the customer", { type: "error" });
    }
  });
}

/* ------------------------------------------------------------ detail view */

function openCustomerDetail(root, ctx, customerId) {
  const customer = state.customers.find((item) => item.id === customerId);
  if (!customer) return;
  const orders = state.orders
    .filter((order) => order.customer_id === customerId)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  const placed = orders.filter((order) => order.status !== "cancelled");
  const spent = placed.reduce((sum, order) => sum + Number(order.total_amount || 0), 0);
  const unpaid = placed.filter((order) => order.payment_status !== "paid" && order.status !== "cancelled");
  const avg = placed.length ? spent / placed.length : 0;

  openModal({
    title: customer.name,
    wide: true,
    body: `
      <div class="stack">
        <div class="stat-grid">
          <div class="stat"><span class="stat__k">Orders placed</span><span class="stat__v">${fmt.num(placed.length)}</span></div>
          <div class="stat"><span class="stat__k">Total purchased</span><span class="stat__v">${esc(fmt.money(spent))}</span></div>
          <div class="stat"><span class="stat__k">Average order</span><span class="stat__v">${placed.length ? esc(fmt.money(avg)) : "—"}</span></div>
          <div class="stat"><span class="stat__k">Awaiting payment</span><span class="stat__v">${fmt.num(unpaid.length)}</span></div>
        </div>

        <div class="form-grid">
          <div>
            <div class="small dim">Phone</div>
            <div style="font-weight:600; color:var(--ink)">${customer.phone ? `<span class="mono">${esc(customer.phone)}</span>` : "—"}</div>
          </div>
          <div>
            <div class="small dim">Email</div>
            <div style="font-weight:600; color:var(--ink)">${customer.email ? esc(customer.email) : "—"}</div>
          </div>
          <div class="span-2">
            <div class="small dim">Delivery address</div>
            <div style="font-weight:600; color:var(--ink)">${customer.address ? esc(customer.address) : "—"}</div>
          </div>
        </div>

        ${
          orders.length
            ? `<div>
                <div class="small dim" style="margin-bottom:6px">Order history · ${orders.length} order${orders.length === 1 ? "" : "s"}</div>
                <div class="table-wrap">
                  <table class="table">
                    <thead><tr><th>Order</th><th>Placed</th><th class="num">Items</th><th class="num">Total</th><th>Payment</th><th>Status</th></tr></thead>
                    <tbody>
                      ${orders
                        .map(
                          (order) => `
                        <tr>
                          <td class="cell-title">#${order.id}${order.is_cod ? ` <span class="reason-tag">COD</span>` : ""}</td>
                          <td><span class="small">${esc(fmt.date(order.created_at))}</span></td>
                          <td class="num">${fmt.num((order.items || []).reduce((sum, item) => sum + item.quantity, 0))}</td>
                          <td class="num"><b>${esc(fmt.money(order.total_amount))}</b></td>
                          <td>${paymentStateBadge(order.payment_status)}</td>
                          <td>${orderStatusBadge(order.status)}</td>
                        </tr>`
                        )
                        .join("")}
                    </tbody>
                  </table>
                </div>
                <p class="hint" style="margin-top:8px">Payments are matched using this customer's phone — keep it accurate.</p>
              </div>`
            : `<div class="pill-note">${icon("info", 14)} No orders yet. When this customer orders, their history appears here.</div>`
        }
      </div>`,
    footer: `
      <button class="btn" data-close-modal>Close</button>
      <button class="btn js-edit-from-detail">${icon("edit", 15)} Edit profile</button>
      <button class="btn btn--primary js-new-order-for">${icon("receipt", 15)} Open Orders</button>`,
  });

  const modal = qs(".modal");
  qs(".js-edit-from-detail", modal).addEventListener("click", () => {
    modal.closest(".modal-scrim")?.remove();
    openCustomerForm(root, ctx, customer);
  });
  qs(".js-new-order-for", modal).addEventListener("click", () => {
    // Hand the customer's name to the Orders page as its search term.
    try {
      sessionStorage.setItem("sf.orders.search", customer.name);
    } catch {
      /* private mode */
    }
    window.location.hash = "#/orders";
  });
}

/* ------------------------------------------------------------ create/edit */

const normPhone = (value) => String(value || "").replace(/\D/g, "");

function findPhoneDuplicates(customerId, phone) {
  const digits = normPhone(phone);
  if (digits.length < 6) return [];
  return state.customers.filter(
    (customer) => customer.id !== customerId && normPhone(customer.phone) === digits
  );
}

function openCustomerForm(root, ctx, customer) {
  const editing = Boolean(customer);
  const { close } = openModal({
    title: editing ? "Edit customer" : "New customer",
    body: `
      <form id="customer-form" novalidate class="stack">
        <div class="form-grid">
          <div class="field span-2">
            <label for="c-name">Full name</label>
            <input class="input" id="c-name" name="name" value="${esc(customer?.name || "")}" autofocus>
          </div>
          <div class="field">
            <label for="c-phone">Phone</label>
            <input class="input" id="c-phone" name="phone" inputmode="tel" value="${esc(customer?.phone || "")}" placeholder="01XXXXXXXXX">
          </div>
          <div class="field">
            <label for="c-email">Email (optional)</label>
            <input class="input" id="c-email" name="email" type="email" value="${esc(customer?.email || "")}">
          </div>
          <div class="field span-2">
            <label for="c-address">Address (optional)</label>
            <input class="input" id="c-address" name="address" value="${esc(customer?.address || "")}" maxlength="500">
          </div>
        </div>
        <div class="pill-note hidden" id="dup-warning">${icon("alert", 14)} <span></span></div>
        <p class="hint">Tip: the customer's phone is used to match bKash payments to their orders automatically.</p>
      </form>`,
    footer: `
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn btn--primary js-save">${icon("check", 15)} ${editing ? "Save changes" : "Create customer"}</button>`,
  });

  const modal = qs(".modal");
  const form = qs("#customer-form", modal);
  const saveButton = qs(".js-save", modal);
  const warning = qs("#dup-warning", modal);
  let duplicateAcknowledged = false;

  qs("#c-phone", modal).addEventListener("input", () => {
    duplicateAcknowledged = false;
    warning.classList.add("hidden");
    saveButton.textContent = "";
    saveButton.innerHTML = `${icon("check", 15)} ${editing ? "Save changes" : "Create customer"}`;
  });

  saveButton.addEventListener("click", async () => {
    clearFieldErrors(form);
    const values = formValues(form);
    if (!values.name) {
      fieldError(form, "name", "Enter a customer name");
      return;
    }

    // Practical duplicate prevention: warn once, then let the seller decide.
    const duplicates = findPhoneDuplicates(customer?.id ?? null, values.phone);
    if (duplicates.length && !duplicateAcknowledged) {
      const names = duplicates.map((item) => item.name).join(", ");
      qs("span", warning).textContent =
        `This number is already saved for ${names}. ` +
        `Matching payments could be ambiguous — use it anyway, or fix the number.`;
      warning.classList.remove("hidden");
      duplicateAcknowledged = true;
      saveButton.innerHTML = `${icon("alert", 15)} Save anyway`;
      return;
    }

    setBusy(saveButton, true, "Saving…");
    try {
      const payload = {
        name: values.name,
        phone: values.phone || null,
        email: values.email || null,
        address: values.address || null,
      };
      if (editing) {
        await api.updateCustomer(ctx.businessId, customer.id, payload);
        toast("Customer updated");
      } else {
        await api.createCustomer(ctx.businessId, payload);
        toast("Customer created");
      }
      close();
      state.customers = await api.customers(ctx.businessId);
      paint(root, ctx);
    } catch (error) {
      setBusy(saveButton, false);
      toast(error.message || "Could not save the customer", { type: "error" });
    }
  });
}
