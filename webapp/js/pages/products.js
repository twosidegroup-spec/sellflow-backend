/* Products — catalogue with image upload support. */

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

let state = { products: [], search: "" };

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="toolbar">
      <div class="input-group grow" style="min-width:min(300px,100%)">
        ${icon("search", 16)}
        <input class="input" id="product-search" aria-label="Search products" placeholder="Search by name or SKU…">
      </div>
      <div class="row-tight">
        <button class="btn js-refresh">${icon("refresh", 15)} Refresh</button>
        <button class="btn btn--primary js-new-product">${icon("plus", 16)} New product</button>
      </div>
    </div>
    <div class="card card--flush"><div id="products-table">${skeleton.table(6)}</div></div>`;

  on(root, "click", ".js-refresh", () => render(root, ctx));
  on(root, "click", ".js-new-product", () => openProductForm(root, ctx, null));
  qs("#product-search", root).addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    paint(root, ctx);
  });

  state.products = await api.products(ctx.businessId);
  paint(root, ctx);
}

function filtered() {
  if (!state.search) return state.products;
  return state.products.filter(
    (product) =>
      product.name.toLowerCase().includes(state.search) ||
      (product.sku || "").toLowerCase().includes(state.search)
  );
}

function paint(root, ctx) {
  const host = qs("#products-table", root);
  const rows = filtered();
  if (!state.products.length) {
    host.innerHTML = emptyState({
      iconName: "box",
      title: "No products yet",
      message: "Add your first product to start creating orders.",
      action: `<button class="btn btn--primary btn--sm js-new-product">${icon("plus", 14)} New product</button>`,
    });
    on(host, "click", ".js-new-product", () => openProductForm(root, ctx, null));
    return;
  }
  if (!rows.length) {
    host.innerHTML = emptyState({ iconName: "search", title: "No matching products", message: "Try a different search term." });
    return;
  }

  host.innerHTML = `
    <div class="table-wrap">
      <table class="table table--cards">
        <thead>
          <tr><th>Product</th><th class="num">Selling price</th><th class="num">Cost</th><th class="num">Margin</th><th class="num">Stock</th><th><span class="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          ${rows
            .map((product) => {
              const price = Number(product.selling_price);
              const cost = Number(product.cost_price);
              const margin = price > 0 ? ((price - cost) / price) * 100 : 0;
              const stock = Number(product.stock_quantity);
              return `
              <tr data-id="${product.id}">
                <td class="cell-lead" data-label="Product">
                  <div class="prod-name">
                    <span class="thumb">${product.image_url ? `<img src="${esc(product.image_url)}" alt="">` : icon("image", 15)}</span>
                    <div class="truncate">
                      <div class="cell-title truncate">${esc(product.name)}</div>
                      <div class="cell-sub mono">${esc(product.sku)}</div>
                    </div>
                  </div>
                </td>
                <td class="num" data-label="Selling price"><b>${esc(fmt.money(price, { decimals: true }))}</b></td>
                <td class="num" data-label="Cost">${esc(fmt.money(cost, { decimals: true }))}</td>
                <td class="num" data-label="Margin">${margin.toFixed(1)}%</td>
                <td class="num" data-label="Stock">${
                  stock === 0
                    ? `<span class="stock-out">Out of stock</span>`
                    : stock <= 5
                      ? `<span class="stock-low">${stock} left</span>`
                      : fmt.num(stock)
                }</td>
                <td data-label="Actions">
                  <div class="row-actions">
                    <button class="icon-btn js-edit" aria-label="Edit ${esc(product.name)}">${icon("edit", 15)}</button>
                    <button class="icon-btn js-delete" aria-label="Delete ${esc(product.name)}">${icon("trash", 15)}</button>
                  </div>
                </td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>`;

  on(host, "click", ".js-edit", (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    openProductForm(root, ctx, state.products.find((product) => product.id === id));
  });
  on(host, "click", ".js-delete", async (event, target) => {
    const id = Number(target.closest("tr").dataset.id);
    const product = state.products.find((item) => item.id === id);
    const confirmed = await confirmDialog({
      title: "Delete product?",
      message: `“${product.name}” will be removed from the catalogue. Existing orders keep their line items.`,
      confirmText: "Delete product",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await api.deleteProduct(ctx.businessId, id);
      toast("Product deleted");
      state.products = state.products.filter((item) => item.id !== id);
      paint(root, ctx);
    } catch (error) {
      toast(error.message || "Could not delete the product", { type: "error" });
    }
  });
}

function openProductForm(root, ctx, product) {
  const editing = Boolean(product);
  const { close } = openModal({
    title: editing ? "Edit product" : "New product",
    body: `
      <form id="product-form" novalidate class="stack">
        <div class="form-grid">
          <div class="field span-2">
            <label for="p-name">Name</label>
            <input class="input" id="p-name" name="name" value="${esc(product?.name || "")}" ${editing ? "" : 'autofocus'}>
          </div>
          <div class="field">
            <label for="p-sku">SKU</label>
            <input class="input" id="p-sku" name="sku" value="${esc(product?.sku || "")}" ${editing ? "disabled" : ""}>
            ${editing ? `<span class="hint">SKU is fixed after creation.</span>` : ""}
          </div>
          <div class="field">
            <label for="p-stock">Stock quantity</label>
            <input class="input" id="p-stock" name="stock_quantity" type="number" min="0" step="1" value="${esc(product?.stock_quantity ?? 0)}">
          </div>
          <div class="field">
            <label for="p-cost">Cost price</label>
            <input class="input" id="p-cost" name="cost_price" type="number" min="0" step="0.01" value="${esc(Number(product?.cost_price ?? 0).toFixed(2))}">
          </div>
          <div class="field">
            <label for="p-price">Selling price</label>
            <input class="input" id="p-price" name="selling_price" type="number" min="0" step="0.01" value="${esc(Number(product?.selling_price ?? 0).toFixed(2))}">
          </div>
          <div class="field span-2">
            <label for="p-desc">Description (optional)</label>
            <input class="input" id="p-desc" name="description" value="${esc(product?.description || "")}" maxlength="1000">
          </div>
          ${
            editing
              ? ""
              : `<div class="field span-2">
                  <label for="p-file">Product image (optional)</label>
                  <input class="input" id="p-file" name="file" type="file" accept="image/png,image/jpeg">
                  <span class="hint">JPG or PNG, up to 10 MB.</span>
                </div>`
          }
        </div>
      </form>`,
    footer: `
      <button class="btn" data-close-modal>Cancel</button>
      <button class="btn btn--primary js-save">${icon("check", 15)} ${editing ? "Save changes" : "Create product"}</button>`,
  });

  const modal = qs(".modal");
  qs(".js-save", modal).addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const form = qs("#product-form", modal);
    clearFieldErrors(form);
    const values = formValues(form);
    let valid = true;
    if (!values.name) { fieldError(form, "name", "Enter a product name"); valid = false; }
    if (!editing && !values.sku) { fieldError(form, "sku", "Enter a SKU"); valid = false; }
    if (Number(values.selling_price) < 0 || values.selling_price === "") { fieldError(form, "selling_price", "Enter a selling price"); valid = false; }
    if (!valid) return;

    setBusy(button, true, "Saving…");
    try {
      if (editing) {
        await api.updateProduct(ctx.businessId, product.id, {
          name: values.name,
          description: values.description || null,
          cost_price: Number(values.cost_price) || 0,
          selling_price: Number(values.selling_price) || 0,
          stock_quantity: Number(values.stock_quantity) || 0,
        });
        toast("Product updated");
      } else {
        const fileInput = qs("#p-file", modal);
        const file = fileInput?.files?.[0];
        if (file) {
          const data = new FormData();
          data.set("name", values.name);
          data.set("sku", values.sku);
          data.set("description", values.description || "");
          data.set("cost_price", values.cost_price || "0");
          data.set("selling_price", values.selling_price || "0");
          data.set("stock_quantity", values.stock_quantity || "0");
          data.set("file", file);
          await api.uploadProduct(ctx.businessId, data);
        } else {
          await api.createProduct(ctx.businessId, {
            name: values.name,
            sku: values.sku,
            description: values.description || null,
            cost_price: Number(values.cost_price) || 0,
            selling_price: Number(values.selling_price) || 0,
            stock_quantity: Number(values.stock_quantity) || 0,
          });
        }
        toast("Product created");
      }
      close();
      state.products = await api.products(ctx.businessId);
      paint(root, ctx);
    } catch (error) {
      setBusy(button, false);
      toast(error.message || "Could not save the product", { type: "error" });
    }
  });
}
