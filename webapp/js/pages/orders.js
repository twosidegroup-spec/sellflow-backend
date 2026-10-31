/* Orders — pipeline, order creation, status flow, manual payments. */

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

let state = {
  orders: [],
  products: [],
  customers: [],
  payments: [],
  filter: "all",
  search: "",
};

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="toolbar">
      <div class="filters-bar grow">
        <div id="status-chips" class="row" style="gap:6px"></div>
        <div class="input-group" style="min-width:min(280px,100%)">
          ${icon("search", 16)}
          <input class="input" id="order-search" aria-label="Search orders" placeholder="Search by order # or customer…">
        </div>
      </div>
      <div class="row-tight">
        <button class="btn js-refresh">${icon("refresh", 15)} Refresh</button>
        <button class="btn btn--primary js-new-order">${icon("plus", 16)} New order</button>
      </div>
    </div>
    <div class="card card--flush"><div id="orders-table">${skeleton.table(6)}</div></div>`;

  on(root, "click", ".js-refresh", () => render(root, ctx));
  on(root, "click", ".js-new-order", () => openCreateOrder(root, ctx));

  qs("#order-search", root).addEventListener(
    "input",
    (event) => {
      state.search = event.target.value.trim().toLowerCase();
      paintRows(root, ctx);
    }
  );

  await load(root, ctx);
}

async function load(root, ctx) {
  const [orders, products, customers, payments] = await Promise.all([
    api.orders(ctx.businessId),
    api.products(ctx.businessId),
    api.customers(ctx.businessId),
    api.payments(ctx.businessId),
  ]);
  state = { ...state, orders, products, customers, payments };
  paintChips(root, ctx);
  paintRows(root, ctx);
}

function paintChips(root, ctx) {
  const counts = { all: state.orders.length };
  for (const status of STATUS_ORDER) {
    counts[status] = state.orders.filter((order) => order.status === status).length;
  }
  qs("#status-chips", root).innerHTML = [
    `<button class="chip ${state.filter === "all" ? "is-active" : ""}" data-filter="all">All <span class="count">${counts.all}</span></button>`,
    ...STATUS_ORDER.filter((status) => counts[status] > 0).map(
      (status) =>
        `<button class="chip ${state.filter === status ? "is-active" : ""}" data-filter="${status}">${STATUS_LABEL[status]} <span class="count">${counts[status]}</span></button>`
    ),
  ].join("");
  qsa("[data-filter]", qs("#status-chips", root)).forEach((chip) =>
    chip.addEventListener("click", () => {
      state.filter = chip.dataset.filter;
      paintChips(root, ctx);
      paintRows(root, ctx);
    })
  );
}

function filtered() {
  return state.orders.filter((order) => {
    if (state.filter !== "all" && order.status !== state.filter) return false;
    if (!state.search) return true;
    const customer = (order.customer?.name || "").toLowerCase();
    return String(order.id).includes(state.search) || customer.includes(state.search);
  });
}

function paintRows(root, ctx) {
  const container = qs("#orders-table", root);
  const rows = filtered();
  if (!state.orders.length) {
    container.innerHTML = emptyState({
      iconName: "receipt",
      title: "No orders yet",
      message: "Create your first order and it will appear here.",
      action: `<button class="btn btn--primary btn--sm js-new-order">${icon("plus", 14)} New order</button>`,
    });
    on(container, "click", ".js-new-order", () => openCreateOrder(root, ctx));
    return;
  }
  if (!rows.length) {
    container.innerHTML = emptyState({ iconName: "search", title: "No matching orders", message: "Try a different filter or search term." });
    return;
  }

  container.innerHTML = `
    <div class="table-wrap">
      <table class="table table--cards">
        <thead>
          <tr>
            <th>Order</th><th>Customer</th><th class="num">Items</th><th class="num">Total</th>
            <th>Payment</th><th>Status</th><th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (order) => `
            <tr data-id="${order.id}">
              <td class="cell-lead" data-label="Order">
                <span class="cell-title">#${order.id}</span>
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

  on(container, "click", ".js-detail", (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    openOrderDetail(root, ctx, id);
  });
  on(container, "click", ".js-menu-btn", (event, target) => {
    event.stopPropagation();
    const id = Number(target.closest("tr").dataset.id);
    openRowMenu(target, root, ctx, id);
  });
}

function openRowMenu(anchor, root, ctx, orderId) {
  qs(".menu-wrap.open")?.remove();
  qs(".row-menu-popover")?.remove();
  const order = state.orders.find((item) => item.id === orderId);
  const rect = anchor.getBoundingClientRect();
  const wrap = document.createElement("div");
  wrap.className = "row-menu-popover";
  wrap.style.position = "fixed";
  wrap.style.zIndex = "120";
  wrap.style.top = `${Math.min(rect.bottom + 6, window.innerHeight - 320)}px`;
  wrap.style.left = `${Math.min(rect.right - 210, window.innerWidth - 224)}px`;
  const statusItems = STATUS_ORDER.filter((status) => status !== order.status)
    .map(
      (status) =>
        `<button class="menu__item" data-status="${status}">${icon("arrowDownRight", 15)} Mark ${STATUS_LABEL[status]}</button>`
    )
    .join("");
  wrap.innerHTML = `
    <div class="menu" style="position:static; animation:none">
      <button class="menu__item" data-action="detail">${icon("eye", 15)} View details</button>
      <button class="menu__item" data-action="pay" ${order.payment_status === "paid" ? "disabled style='opacity:.5'" : ""}>${icon("wallet", 15)} Record payment</button>
      <div class="menu__sep"></div>
      ${statusItems}
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

function openOrderDetail(root, ctx, orderId) {
  const order = state.orders.find((item) => item.id === orderId);
  if (!order) return;
  const payments = state.payments.filter((payment) => payment.order_id === orderId);
  openModal({
    title: `Order #${order.id}`,
    wide: true,
    body: `
      <div class="stack">
        <div class="spread">
          <div class="row-tight">${orderStatusBadge(order.status)} ${paymentStateBadge(order.payment_status)}</div>
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
            : `<div class="pill-note">${icon("info", 14)} No payment recorded for this order yet.</div>`
        }
        ${order.notes ? `<div class="pill-note">${icon("fileText", 14)} ${esc(order.notes)}</div>` : ""}
      </div>`,
    footer: `
      <button class="btn" data-close-modal>Close</button>
      ${order.payment_status !== "paid" ? `<button class="btn btn--primary js-pay-in-modal">${icon("wallet", 15)} Record payment</button>` : ""}`,
    onMount: ({ body, close }) => {
      qs(".js-pay-in-modal", body.parentElement || body)?.addEventListener("click", () => {
        close();
        openRecordPayment(root, ctx, orderId);
      });
    },
  });
}

/* --------------------------------------------------------- create an order */

function openCreateOrder(root, ctx) {
  if (!state.products.length) {
    toast("Add a product first — orders are built from your catalogue.", { type: "warn", title: "No products yet" });
    window.location.hash = "#/products";
    return;
  }

  const customerOptions = [
    `<option value="">Walk-in customer</option>`,
    ...state.customers.map((customer) => `<option value="${customer.id}">${esc(customer.name)}</option>`),
  ].join("");
  const productOptions = state.products
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
        <div class="totals-box" id="order-totals"></div>
      </form>`,
    footer: `
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn btn--primary js-save-order">${icon("check", 15)} Create order</button>`,
  });

  const modal = qs(".modal");
  const itemsHost = qs("#items", modal);
  const totalsHost = qs("#order-totals", modal);

  function addItem() {
    const line = document.createElement("div");
    line.className = "item-line";
    line.innerHTML = `
      <select class="select js-product">${productOptions}</select>
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
      };
      const customerId = qs("#customer_id", modal).value;
      if (customerId) payload.customer_id = Number(customerId);
      const order = await api.createOrder(ctx.businessId, payload);
      close();
      toast(`Order #${order.id} created`, { title: "Order added" });
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
      const message = error instanceof ApiError ? error.message : "Could not record the payment";
      toast(message, { type: "error" });
    }
  });
}
