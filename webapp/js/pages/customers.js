/* Customers — directory with create/edit and safe delete. */

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
  qs,
  setBusy,
  skeleton,
  toast,
} from "../ui.js";

let state = { customers: [], search: "" };

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="toolbar">
      <div class="input-group grow" style="min-width:min(300px,100%)">
        ${icon("search", 16)}
        <input class="input" id="customer-search" aria-label="Search customers" placeholder="Search by name, phone or email…">
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

  state.customers = await api.customers(ctx.businessId);
  paint(root, ctx);
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
          <tr><th>Customer</th><th>Phone</th><th>Email</th><th>Address</th><th>Added</th><th><span class="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (customer) => `
            <tr data-id="${customer.id}">
              <td class="cell-lead" data-label="Customer">
                <div class="row-tight">
                  <span class="avatar">${esc(fmt.initials(customer.name))}</span>
                  <div>
                    <div class="cell-title">${esc(customer.name)}</div>
                    <div class="cell-sub">Customer #${customer.id}</div>
                  </div>
                </div>
              </td>
              <td data-label="Phone">${customer.phone ? `<span class="mono small">${esc(customer.phone)}</span>` : `<span class="dim">—</span>`}</td>
              <td data-label="Email">${customer.email ? esc(customer.email) : `<span class="dim">—</span>`}</td>
              <td data-label="Address">${customer.address ? `<span class="truncate" style="display:inline-block; max-width:220px">${esc(customer.address)}</span>` : `<span class="dim">—</span>`}</td>
              <td data-label="Added"><span class="small dim">${esc(fmt.date(customer.created_at))}</span></td>
              <td data-label="Actions">
                <div class="row-actions">
                  <button class="icon-btn js-edit" aria-label="Edit ${esc(customer.name)}">${icon("edit", 15)}</button>
                  <button class="icon-btn js-delete" aria-label="Delete ${esc(customer.name)}">${icon("trash", 15)}</button>
                </div>
              </td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;

  on(host, "click", ".js-edit", (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    openCustomerForm(root, ctx, state.customers.find((customer) => customer.id === id));
  });
  on(host, "click", ".js-delete", async (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    const customer = state.customers.find((item) => item.id === id);
    const confirmed = await confirmDialog({
      title: "Delete customer?",
      message: `“${customer.name}” will be removed from your directory. Orders keep their history.`,
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
        <p class="hint">Tip: the customer's phone is used to match bKash payments to their orders automatically.</p>
      </form>`,
    footer: `
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn btn--primary js-save">${icon("check", 15)} ${editing ? "Save changes" : "Create customer"}</button>`,
  });

  const modal = qs(".modal");
  qs(".js-save", modal).addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const form = qs("#customer-form", modal);
    clearFieldErrors(form);
    const values = formValues(form);
    if (!values.name) {
      fieldError(form, "name", "Enter a customer name");
      return;
    }
    setBusy(button, true, "Saving…");
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
      setBusy(button, false);
      toast(error.message || "Could not save the customer", { type: "error" });
    }
  });
}
