/* Orders — server-filtered pipeline, order creation, status flow, COD,
   courier/tracking, manual payments. */

import { api, ApiError } from "../api.js";
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
  qsa,
  setBusy,
  skeleton,
  toast,
} from "../ui.js";

const STATUS_ORDER = ["created", "confirmed", "packed", "shipped", "delivered", "cancelled"];
const STATUS_LABEL = {
  created: "New",
  confirmed: "Confirmed",
  packed: "Packed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};
const SORT_OPTIONS = {
  newest: "Newest first",
  oldest: "Oldest first",
  amount_desc: "Highest total",
  amount_asc: "Lowest total",
};
const COURIERS = ["Pathao", "Steadfast", "RedX", "Sundarban", "Paperfly", "Other"];
const DELIVERY_STATUS = {
  pending: "Pending",
  picked_up: "Picked up",
  in_transit: "In transit",
  delivered: "Delivered",
  returned: "Returned",
  failed: "Failed",
};

const PAGE_SIZE = 25;

let state = {
  orders: [],
  products: [],
  customers: [],
  payments: [],
  counts: {},
  status: "",
  q: "",
  sort: "newest",
  offset: 0,
  hasMore: false,
  loading: false,
};

export async function render(root, ctx) {
  // Deep link from the Customers module ("Open Orders" with a search term).
  try {
    const pendingSearch = sessionStorage.getItem("sf.orders.search");
    if (pendingSearch) {
      sessionStorage.removeItem("sf.orders.search");
      state.q = pendingSearch;
      state.offset = 0;
    }
  } catch {
    /* private mode */
  }

  root.innerHTML = `
    <div class="toolbar">
      <div class="filters-bar grow">
        <div id="status-chips" class="row" style="gap:6px"></div>
        <div class="input-group" style="min-width:min(260px,100%)">
          ${icon("search", 16)}
          <input class="input" id="order-search" aria-label="Search orders" placeholder="Search order # or customer…" value="${esc(state.q)}">
        </div>
        <select class="select" id="order-sort" aria-label="Sort orders" style="width:auto">
          ${Object.entries(SORT_OPTIONS)
            .map(([value, label]) => `<option value="${value}" ${state.sort === value ? "selected" : ""}>${esc(label)}</option>`)
            .join("")}
        </select>
      </div>
      <div class="row-tight">
        <button class="btn js-refresh">${icon("refresh", 15)} Refresh</button>
        <button class="btn btn--primary js-new-order">${icon("plus", 16)} New order</button>
      </div>
    </div>
    <div class="card card--flush">
      <div id="orders-table">${skeleton.table(6)}</div>
      <div class="pagination" id="orders-pager"></div>
    </div>`;

  on(root, "click", ".js-refresh", () => load(root, ctx));
  on(root, "click", ".js-new-order", () => openCreateOrder(root, ctx));

  const search = qs("#order-search", root);
  let timer;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.q = search.value.trim();
      state.offset = 0;
      load(root, ctx);
    }, 300);
  });
  qs("#order-sort", root).addEventListener("change", (event) => {
    state.sort = event.target.value;
    state.offset = 0;
    load(root, ctx);
  });

  await load(root, ctx);
}

async function load(root, ctx) {
  state.loading = true;
  paintChips(root);
  try {
    const [orders, products, customers, payments, summary] = await Promise.all([
      api.orders(ctx.businessId, {
        status: state.status || undefined,
        q: state.q || undefined,
        sort: state.sort,
        limit: PAGE_SIZE,
        offset: state.offset,
      }),
      api.products(ctx.businessId),
      api.customers(ctx.businessId),
      api.payments(ctx.businessId),
      api.summary(ctx.businessId).catch(() => null),
    ]);
    state.orders = orders;
    state.hasMore = orders.length === PAGE_SIZE;
    state.products = products;
    state.customers = customers;
    state.payments = payments;
    state.counts = summary?.orders_by_status || {};
    state.counts.all = summary?.total_orders ?? null;
  } finally {
    state.loading = false;
  }
  paintChips(root);
  paintRows(root, ctx);
  paintPager(root, ctx);
}

function paintChips(root) {
  const host = qs("#status-chips", root);
  if (!host) return;
  const counts = state.counts || {};
  const chip = (key, label, count) => `
    <button class="chip ${state.status === key ? "is-active" : ""}" data-filter="${key}">
      ${esc(label)}${Number.isFinite(count) ? ` <span class="count">${fmt.num(count)}</span>` : ""}
    </button>`;
  host.innerHTML = [
    chip("", "All", Number.isFinite(counts.all) ? counts.all : NaN),
    ...STATUS_ORDER.filter((status) => (counts[status] || 0) > 0 || state.status === status).map(
      (status) => chip(status, STATUS_LABEL[status], counts[status] || 0)
    ),
  ].join("");
  qsa("[data-filter]", host).forEach((node) =>
    node.addEventListener("click", () => {
      state.status = node.dataset.filter;
      state.offset = 0;
      load(root, ctxFrom(root));
    })
  );
}

function ctxFrom(root) {
  return { businessId: api.businessId, user: api.user };
}

function paintRows(root, ctx) {
  const host = qs("#orders-table", root);
  if (state.loading && !state.orders.length) {
    host.innerHTML = skeleton.table(6);
    return;
  }
  if (!state.orders.length) {
    host.innerHTML = emptyState({
      iconName: state.q || state.status ? "search" : "receipt",
      title: state.q || state.status ? "No matching orders" : "No orders yet",
      message:
        state.q || state.status
          ? "Try a different filter or search term."
          : "Create your first order and it will appear here.",
      action: state.q || state.status ? "" : `<button class="btn btn--primary btn--sm js-new-order">${icon("plus", 14)} New order</button>`,
    });
    on(host, "click", ".js-new-order", () => openCreateOrder(root, ctx));
    return;
  }

  host.innerHTML = `
    <div class="table-wrap">
      <table class="table table--cards">
        <thead>
          <tr>
            <th>Order</th><th>Customer</th><th class="num">Items</th><th class="num">Total</th>
            <th>Payment</th><th>Status</th><th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          ${state.orders
            .map(
              (order) => `
            <tr data-id="${order.id}">
              <td class="cell-lead" data-label="Order">
                <span class="cell-title">#${order.id}${order.is_cod ? ` <span class="reason-tag">COD</span>` : ""}</span>
                <span class="cell-sub">${esc(fmt.relative(order.created_at))}${order.notes ? " · has note" : ""}</span>
              </td>
              <td data-label="Customer">${esc(order.customer?.name || "Walk-in")}</td>
              <td class="num" data-label="Items">${fmt.num((order.items || []).reduce((sum, item) => sum + item.quantity, 0))}</td>
              <td class="num" data-label="Total"><b>${esc(fmt.money(order.total_amount, { decimals: true }))}</b></td>
              <td data-label="Payment">${paymentStateBadge(order.payment_status)}</td>
              <td data-label="Status">${orderStatusBadge(order.status)}</td>
              <td data-label="Actions">
                <div class="row-actions">
                  <button class="icon-btn js-detail" title="View details" aria-label="View order ${order.id}">${icon("eye", 16)}</button>
                  <button class="icon-btn js-menu-btn" title="More actions" aria-label="More actions for order ${order.id}">${icon("moreH", 16)}</button>
                </div>
              </td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;

  on(host, "click", ".js-detail", (event, target) => {
    openOrderDetail(root, ctx, Number(target.closest("tr").dataset.id));
  });
  on(host, "click", ".js-menu-btn", (event, target) => {
    event.stopPropagation();
    openRowMenu(target, root, ctx, Number(target.closest("tr").dataset.id));
  });
}

function paintPager(root, ctx) {
  const host = qs("#orders-pager", root);
  if (!host) return;
  const from = state.offset + 1;
  const to = state.offset + state.orders.length;
  host.innerHTML = `
    <span class="small dim">${state.orders.length ? `Showing ${from}–${to}` : "No orders on this page"}</span>
    <button class="btn btn--sm js-prev" ${state.offset === 0 ? "disabled" : ""}>${icon("chevronLeft", 14)} Previous</button>
    <button class="btn btn--sm js-next" ${state.hasMore ? "" : "disabled"}>Next ${icon("chevronRight", 14)}</button>`;
  qs(".js-prev", host).addEventListener("click", () => {
    state.offset = Math.max(0, state.offset - PAGE_SIZE);
    load(root, ctx);
  });
  qs(".js-next", host).addEventListener("click", () => {
    state.offset += PAGE_SIZE;
    load(root, ctx);
  });
}

/* ------------------------------------------------------------- row menu -- */

/* Order-status transition policy (mirrors app/orders/models.py;
   STAGING_READINESS.md 4.1). Same-status requests are no-ops and are not
   offered. Terminal states allow nothing. */
const ALLOWED_TRANSITIONS = {
  created: ["confirmed", "cancelled"],
  confirmed: ["packed", "shipped", "cancelled"],
  packed: ["shipped", "cancelled"],
  shipped: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};

function allowedNextStatuses(current) {
  return ALLOWED_TRANSITIONS[current] || [];
}

function openRowMenu(anchor, root, ctx, orderId) {
  qs(".row-menu-popover")?.remove();
  const order = state.orders.find((item) => item.id === orderId);
  if (!order) return;
  const rect = anchor.getBoundingClientRect();
  const nextStatuses = allowedNextStatuses(order.status);
  const wrap = document.createElement("div");
  wrap.className = "row-menu-popover";
  wrap.style.position = "fixed";
  wrap.style.zIndex = "120";
  wrap.style.top = `${Math.min(rect.bottom + 6, window.innerHeight - 340)}px`;
  wrap.style.left = `${Math.min(rect.right - 210, window.innerWidth - 224)}px`;
  wrap.innerHTML = `
    <div class="menu" style="position:static; animation:none">
      <button class="menu__item" data-action="detail">${icon("eye", 15)} View details</button>
      <button class="menu__item" data-action="pay" ${order.payment_status === "paid" ? "disabled style='opacity:.5'" : ""}>${icon("wallet", 15)} Record payment</button>
      ${
        nextStatuses.length
          ? `<div class="menu__sep"></div>
             ${nextStatuses
               .map((status) => `<button class="menu__item" data-status="${status}">${icon("arrowDownRight", 15)} Mark ${STATUS_LABEL[status]}</button>`)
               .join("")}`
          : ""
      }
    </div>`;
  document.body.appendChild(wrap);

  const close = () => wrap.remove();
  const onDocClick = (event) => {
    if (!wrap.contains(event.target)) {
      close();
      document.removeEventListener("click", onDocClick);
    }
  };
  setTimeout(() => document.addEventListener("click", onDocClick), 0);
  window.addEventListener("scroll", close, { once: true, capture: true });

  wrap.addEventListener("click", async (event) => {
    const statusButton = event.target.closest("[data-status]");
    const actionButton = event.target.closest("[data-action]");
    if (statusButton) {
      close();
      const status = statusButton.dataset.status;
      if (status === "cancelled") {
        const confirmed = await confirmDialog({
          title: `Cancel order #${orderId}?`,
          message: "Cancelling keeps the record but excludes it from revenue and profit.",
          confirmText: "Cancel order",
          danger: true,
        });
        if (!confirmed) return;
      }
      try {
        await api.setOrderStatus(ctx.businessId, orderId, status);
        toast(`Order #${orderId} → ${STATUS_LABEL[status]}`);
        await load(root, ctx);
      } catch (error) {
        toast(error.message || "Could not update the order", { type: "error" });
      }
    } else if (actionButton?.dataset.action === "detail") {
      close();
      openOrderDetail(root, ctx, orderId);
    } else if (actionButton?.dataset.action === "pay") {
      close();
      openRecordPayment(root, ctx, orderId);
    }
  });
}

/* ------------------------------------------------------------ order detail */

async function openOrderDetail(root, ctx, orderId) {
  const order = state.orders.find((item) => item.id === orderId);
  if (!order) return;
  let delivery = null;
  try {
    delivery = await api.delivery(ctx.businessId, orderId);
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) {
      delivery = null;
    }
  }
  const payments = state.payments.filter((payment) => payment.order_id === orderId);

  const { body } = openModal({
    title: `Order #${order.id}`,
    wide: true,
    body: `
      <div class="stack">
        <div class="spread">
          <div class="row-tight">
            ${orderStatusBadge(order.status)} ${paymentStateBadge(order.payment_status)}
            ${order.is_cod ? `<span class="badge badge--warn">Cash on delivery</span>` : `<span class="badge badge--info">Prepaid</span>`}
          </div>
          <div class="small dim">Placed ${esc(fmt.dateTime(order.created_at))}</div>
        </div>
        <div class="form-grid">
          <div><div class="small dim">Customer</div><div style="font-weight:600; color:var(--ink)">${esc(order.customer?.name || "Walk-in")}</div></div>
          <div><div class="small dim">Delivery fee</div><div style="font-weight:600; color:var(--ink)">${esc(fmt.money(order.delivery_fee, { decimals: true }))}</div></div>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>Item</th><th class="num">Qty</th><th class="num">Unit</th><th class="num">Line total</th></tr></thead>
            <tbody>
              ${(order.items || [])
                .map(
                  (item) => `
                <tr>
                  <td class="cell-title">${esc(item.product_name)}</td>
                  <td class="num">${fmt.num(item.quantity)}</td>
                  <td class="num">${esc(fmt.money(item.unit_price, { decimals: true }))}</td>
                  <td class="num"><b>${esc(fmt.money(item.line_total, { decimals: true }))}</b></td>
                </tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
        <div class="totals-box">
          <div class="rowline"><span>Delivery fee</span><span class="num">${esc(fmt.moneyExact(order.delivery_fee))}</span></div>
          ${Number(order.discount) > 0 ? `<div class="rowline"><span>Discount</span><span class="num">−${esc(fmt.moneyExact(order.discount))}</span></div>` : ""}
          <div class="rowline total"><span>Order total</span><span class="num">${esc(fmt.moneyExact(order.total_amount))}</span></div>
        </div>

        <div class="card" style="box-shadow:none">
          <div class="card__head" style="padding:12px 16px">
            <div><h2 style="font-size:var(--fs-14)">Delivery</h2><div class="sub">${delivery ? `${esc(DELIVERY_STATUS[delivery.status] || delivery.status)} · ${esc(delivery.courier || "no courier yet")}` : "Not arranged yet"}</div></div>
          </div>
          <div class="card__body" style="padding:16px">
            <form id="delivery-form" class="form-grid">
              <div class="field">
                <label for="d-courier">Courier</label>
                <select class="select" id="d-courier" name="courier">
                  <option value="">Not chosen</option>
                  ${COURIERS.map((courier) => `<option value="${esc(courier)}" ${delivery?.courier === courier ? "selected" : ""}>${esc(courier)}</option>`).join("")}
                </select>
              </div>
              <div class="field">
                <label for="d-tracking">Tracking reference</label>
                <input class="input" id="d-tracking" name="tracking_number" value="${esc(delivery?.tracking_number || "")}" placeholder="e.g. PTH-00291">
              </div>
              ${delivery
                ? `<div class="field span-2">
                    <label for="d-status">Delivery status</label>
                    <select class="select" id="d-status" name="status">
                      ${Object.entries(DELIVERY_STATUS)
                        .map(([value, label]) => `<option value="${value}" ${delivery.status === value ? "selected" : ""}>${label}</option>`)
                        .join("")}
                    </select>
                  </div>`
                : `<div class="field span-2">
                    <label for="d-fee">Delivery fee charged</label>
                    <input class="input" id="d-fee" name="delivery_fee" type="number" min="0" step="0.01" value="${Number(order.delivery_fee).toFixed(2)}">
                  </div>`}
            </form>
          </div>
          <div class="card__foot" style="padding:12px 16px">
            <span class="small dim">${delivery ? "Update the parcel as it moves." : "Create the delivery record when you hand the parcel over."}</span>
            <button class="btn btn--sm btn--primary js-save-delivery" type="button">${icon("truck", 14)} ${delivery ? "Update delivery" : "Save delivery"}</button>
          </div>
        </div>

        ${
          payments.length
            ? `<div>
                <div class="small dim" style="margin-bottom:6px">Payments recorded</div>
                ${payments
                  .map(
                    (payment) => `
                  <div class="provider-row">
                    <span class="thumb">${icon("wallet", 15)}</span>
                    <div class="grow">
                      <div style="font-weight:600; color:var(--ink)">${esc(fmt.money(payment.amount, { decimals: true }))} <span class="dim" style="font-weight:500">· ${esc(payment.method)}</span></div>
                      <div class="small dim mono">${esc(payment.transaction_id || "no reference")}</div>
                    </div>
                    <div class="small dim">${esc(fmt.dateTime(payment.paid_at || payment.created_at))}</div>
                  </div>`
                  )
                  .join("")}
              </div>`
            : `<div class="pill-note">${icon("info", 14)} No payment recorded for this order yet.${order.is_cod ? " This is a COD order — collect on delivery, then record the payment." : ""}</div>`
        }
        ${order.notes ? `<div class="pill-note">${icon("fileText", 14)} ${esc(order.notes)}</div>` : ""}
      </div>`,
    footer: `
      <button class="btn" data-close-modal>Close</button>
      ${order.payment_status !== "paid" ? `<button class="btn btn--primary js-pay-in-modal">${icon("wallet", 15)} Record payment</button>` : ""}`,
  });

  const modal = qs(".modal");
  qs(".js-pay-in-modal", modal)?.addEventListener("click", () => {
    body.closest(".modal-scrim")?.remove();
    openRecordPayment(root, ctx, orderId);
  });

  qs(".js-save-delivery", modal).addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const courier = qs("#d-courier", modal).value || null;
    const tracking = qs("#d-tracking", modal).value.trim() || null;
    setBusy(button, true, "Saving…");
    try {
      if (delivery) {
        await api.updateDelivery(ctx.businessId, orderId, {
          courier,
          tracking_number: tracking,
          status: qs("#d-status", modal).value,
        });
        toast("Delivery updated");
      } else {
        await api.createDelivery(ctx.businessId, orderId, {
          courier,
          tracking_number: tracking,
          delivery_fee: Number(qs("#d-fee", modal).value) || 0,
        });
        toast("Delivery recorded");
      }
      body.closest(".modal-scrim")?.remove();
      openOrderDetail(root, ctx, orderId);
    } catch (error) {
      setBusy(button, false);
      toast(error.message || "Could not save the delivery", { type: "error" });
    }
  });
}

/* --------------------------------------------------------- create an order */

function openCreateOrder(root, ctx) {
  const activeProducts = state.products.filter((product) => (product.status || "active") === "active");
  if (!activeProducts.length) {
    toast("Add an active product first — orders are built from your catalogue.", { type: "warn", title: "No products available" });
    window.location.hash = "#/products";
    return;
  }

  const customerOptions = [
    `<option value="">Walk-in customer</option>`,
    ...state.customers.map((customer) => `<option value="${customer.id}">${esc(customer.name)}</option>`),
  ].join("");
  const productOptions = activeProducts
    .map((product) => `<option value="${product.id}" data-price="${product.selling_price}" data-cost="${product.cost_price}">${esc(product.name)}</option>`)
    .join("");

  const { close } = openModal({
    title: "New order",
    wide: true,
    body: `
      <form id="order-form" novalidate class="stack">
        <div class="form-grid">
          <div class="field">
            <label for="customer_id">Customer</label>
            <select class="select" id="customer_id" name="customer_id">${customerOptions}</select>
          </div>
          <div class="field">
            <label for="notes">Note (optional)</label>
            <input class="input" id="notes" name="notes" placeholder="Delivery instructions, colour…">
          </div>
        </div>
        <div class="field">
          <label>Items</label>
          <div class="items-editor" id="items"></div>
          <button type="button" class="btn btn--sm js-add-item" style="align-self:flex-start">${icon("plus", 14)} Add item</button>
        </div>
        <div class="form-grid">
          <div class="field">
            <label for="delivery_fee">Delivery fee</label>
            <input class="input" id="delivery_fee" name="delivery_fee" type="number" min="0" step="0.01" value="0">
          </div>
          <div class="field">
            <label for="discount">Discount</label>
            <input class="input" id="discount" name="discount" type="number" min="0" step="0.01" value="0">
          </div>
        </div>
        <label class="checkline" style="margin-top:-4px">
          <input type="checkbox" id="is_cod" name="is_cod">
          Cash on delivery (collect payment when the parcel arrives)
        </label>
        <div class="totals-box" id="order-totals"></div>
      </form>`,
    footer: `
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn btn--primary js-save-order">${icon("check", 15)} Create order</button>`,
  });

  const modal = qs(".modal");
  const itemsHost = qs("#items", modal);
  const totalsHost = qs("#order-totals", modal);

  function readItems() {
    return qsa(".item-line", itemsHost).map((line) => {
      const select = qs(".js-product", line);
      const product = state.products.find((item) => String(item.id) === select.value);
      const quantity = Math.max(1, parseInt(qs(".js-qty", line).value, 10) || 1);
      const unitPrice = Number(qs(".js-price", line).value) || 0;
      return {
        product_id: product?.id ?? null,
        product_name: product?.name || "Item",
        quantity,
        unit_price: unitPrice,
        unit_cost: Number(product?.cost_price || 0),
      };
    });
  }

  function paintTotals() {
    const items = readItems();
    const subtotal = items.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);
    const fee = Number(qs("#delivery_fee", modal).value) || 0;
    const discount = Number(qs("#discount", modal).value) || 0;
    const total = Math.max(0, subtotal + fee - discount);
    totalsHost.innerHTML = `
      <div class="rowline"><span>Subtotal</span><span class="num">${esc(fmt.moneyExact(subtotal))}</span></div>
      <div class="rowline"><span>Delivery fee</span><span class="num">${esc(fmt.moneyExact(fee))}</span></div>
      <div class="rowline"><span>Discount</span><span class="num">−${esc(fmt.moneyExact(discount))}</span></div>
      <div class="rowline total"><span>Order total</span><span class="num">${esc(fmt.moneyExact(total))}</span></div>`;
  }

  function addItem() {
    const line = document.createElement("div");
    line.className = "item-line";
    line.innerHTML = `
      <select class="select js-product" aria-label="Product">${productOptions}</select>
      <input class="input js-qty" type="number" min="1" step="1" value="1" aria-label="Quantity">
      <input class="input js-price" type="number" min="0" step="0.01" aria-label="Unit price">
      <button type="button" class="icon-btn js-remove" aria-label="Remove item">${icon("trash", 15)}</button>`;
    itemsHost.appendChild(line);
    const select = qs(".js-product", line);
    const priceInput = qs(".js-price", line);
    priceInput.value = Number(select.selectedOptions[0]?.dataset.price || 0).toFixed(2);
    select.addEventListener("change", () => {
      priceInput.value = Number(select.selectedOptions[0]?.dataset.price || 0).toFixed(2);
      paintTotals();
    });
    qs(".js-qty", line).addEventListener("input", paintTotals);
    priceInput.addEventListener("input", paintTotals);
    qs(".js-remove", line).addEventListener("click", () => {
      line.remove();
      paintTotals();
    });
    paintTotals();
  }

  qs(".js-add-item", modal).addEventListener("click", addItem);
  qs("#delivery_fee", modal).addEventListener("input", paintTotals);
  qs("#discount", modal).addEventListener("input", paintTotals);
  addItem();

  qs(".js-save-order", modal).addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const items = readItems();
    if (!items.length) {
      toast("Add at least one item", { type: "warn" });
      return;
    }
    setBusy(button, true, "Creating…");
    try {
      const payload = {
        items,
        delivery_fee: Number(qs("#delivery_fee", modal).value) || 0,
        discount: Number(qs("#discount", modal).value) || 0,
        notes: qs("#notes", modal).value.trim() || null,
        is_cod: qs("#is_cod", modal).checked,
      };
      const customerId = qs("#customer_id", modal).value;
      if (customerId) payload.customer_id = Number(customerId);
      const order = await api.createOrder(ctx.businessId, payload);
      close();
      toast(`Order #${order.id} created${payload.is_cod ? " · cash on delivery" : ""}`, { title: "Order added" });
      state.offset = 0;
      await load(root, ctx);
    } catch (error) {
      setBusy(button, false);
      toast(error.message || "Could not create the order", { type: "error" });
    }
  });
}

/* -------------------------------------------------------- record a payment */

function openRecordPayment(root, ctx, orderId) {
  const order = state.orders.find((item) => item.id === orderId);
  if (!order) return;
  const methods = ["bkash", "nagad", "rocket", "upay", "cash"]
    .map((method) => `<option value="${method}">${esc(method === "bkash" ? "bKash" : method[0].toUpperCase() + method.slice(1))}</option>`)
    .join("");

  const { close } = openModal({
    title: `Record payment — order #${order.id}`,
    body: `
      <form id="payment-form" novalidate class="stack">
        <div class="pill-note">${icon("info", 14)} Order total ${esc(fmt.money(order.total_amount, { decimals: true }))}. Recording a payment marks the order as paid.</div>
        <div class="form-grid">
          <div class="field">
            <label for="pay-amount">Amount received</label>
            <input class="input" id="pay-amount" name="amount" type="number" min="0.01" step="0.01" value="${Number(order.total_amount).toFixed(2)}">
          </div>
          <div class="field">
            <label for="pay-method">Method</label>
            <select class="select" id="pay-method" name="method">${methods}</select>
          </div>
          <div class="field span-2">
            <label for="pay-txid">Transaction ID (bKash TrxID …)</label>
            <input class="input" id="pay-txid" name="transaction_id" placeholder="Optional but recommended">
          </div>
          <div class="field span-2">
            <label for="pay-notes">Note (optional)</label>
            <input class="input" id="pay-notes" name="notes" maxlength="500">
          </div>
        </div>
      </form>`,
    footer: `
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn btn--primary js-save-payment">${icon("check", 15)} Record payment</button>`,
  });

  const modal = qs(".modal");
  qs(".js-save-payment", modal).addEventListener("click", async (event) => {
    const button = event.currentTarget;
    clearFieldErrors(modal);
    const values = formValues(qs("#payment-form", modal));
    if (!values.amount || Number(values.amount) <= 0) {
      fieldError(qs("#payment-form", modal), "amount", "Enter the amount received");
      return;
    }
    setBusy(button, true, "Recording…");
    try {
      await api.recordPayment(ctx.businessId, orderId, {
        amount: Number(values.amount),
        method: values.method,
        transaction_id: values.transaction_id || null,
        notes: values.notes || null,
      });
      close();
      toast(`Payment recorded for order #${orderId}`, { title: "Payment saved" });
      await load(root, ctx);
    } catch (error) {
      setBusy(button, false);
      toast(error instanceof ApiError ? error.message : "Could not record the payment", { type: "error" });
    }
  });
}
