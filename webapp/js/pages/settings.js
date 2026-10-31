/* Settings — profile, business, payments, security, appearance. */

import { api } from "../api.js";
import {
  clearFieldErrors,
  copyText,
  esc,
  fieldError,
  fmt,
  formValues,
  icon,
  on,
  providerLabel,
  qs,
  qsa,
  setBusy,
  skeleton,
  toast,
} from "../ui.js";
import { providerLogo } from "./payments.js";

let section = "profile";

const SECTIONS = [
  ["profile", "Profile", "users"],
  ["business", "Business", "bank"],
  ["payments", "Payments", "wallet"],
  ["security", "Security", "shield"],
  ["notifications", "Notifications", "bell"],
  ["data", "Data", "download"],
  ["appearance", "Appearance", "sun"],
];

export async function render(root, ctx) {
  root.innerHTML = `
    <div class="settings-grid">
      <nav class="settings-nav" id="settings-nav" aria-label="Settings sections">
        ${SECTIONS.map(
          ([key, label, iconName]) =>
            `<button data-section="${key}" class="${section === key ? "is-active" : ""}">${icon(iconName, 16)} ${esc(label)}</button>`
        ).join("")}
      </nav>
      <div id="settings-panel">${skeleton.table(5)}</div>
    </div>`;

  on(root, "click", "[data-section]", (event, target) => {
    section = target.dataset.section;
    qsa("#settings-nav button", root).forEach((button) =>
      button.classList.toggle("is-active", button.dataset.section === section)
    );
    paintPanel(root, ctx);
  });

  await paintPanel(root, ctx);
}

async function paintPanel(root, ctx) {
  const panel = qs("#settings-panel", root);
  const user = await api.me();
  ctx.user = user;
  if (section === "profile") return renderProfile(panel, user);
  if (section === "business") return renderBusiness(panel, ctx, user);
  if (section === "payments") return renderPayments(panel, ctx, user);
  if (section === "security") return renderSecurity(panel);
  if (section === "notifications") return renderNotifications(panel);
  if (section === "data") return renderData(panel, ctx);
  return renderAppearance(panel);
}

/* ----------------------------------------------------------------- profile */

function renderProfile(panel, user) {
  panel.innerHTML = `
    <div class="card">
      <div class="card__head"><div><h2>Profile</h2><div class="sub">How you appear inside the console</div></div></div>
      <div class="card__body">
        <div class="row" style="margin-bottom:var(--sp-5)">
          <span class="avatar avatar--lg avatar--navy">${esc(fmt.initials(user.full_name))}</span>
          <div>
            <div style="font-weight:700; color:var(--ink); font-size:var(--fs-16)">${esc(user.full_name)}</div>
            <div class="small dim">${esc(user.email)}</div>
          </div>
        </div>
        <form id="profile-form" novalidate class="form-grid">
          <div class="field">
            <label for="pf-name">Full name</label>
            <input class="input" id="pf-name" name="full_name" value="${esc(user.full_name || "")}">
          </div>
          <div class="field">
            <label for="pf-phone">Phone</label>
            <input class="input" id="pf-phone" name="phone" inputmode="tel" value="${esc(user.phone || "")}">
          </div>
          <div class="field span-2">
            <label for="pf-email">Email</label>
            <input class="input" id="pf-email" value="${esc(user.email || "")}" disabled>
            <span class="hint">Email is your sign-in identifier and cannot be changed here.</span>
          </div>
        </form>
      </div>
      <div class="card__foot">
        <span class="small dim">Changes apply to this account only.</span>
        <button class="btn btn--primary js-save-profile">${icon("check", 15)} Save profile</button>
      </div>
    </div>`;

  qs(".js-save-profile", panel).addEventListener("click", async (event) => {
    const form = qs("#profile-form", panel);
    clearFieldErrors(form);
    const values = formValues(form);
    if (!values.full_name) {
      fieldError(form, "full_name", "Enter your name");
      return;
    }
    setBusy(event.currentTarget, true, "Saving…");
    try {
      await api.updateMe({ full_name: values.full_name, phone: values.phone || null });
      toast("Profile updated");
      window.dispatchEvent(new CustomEvent("sf:profile-updated"));
    } catch (error) {
      toast(error.message || "Could not save the profile", { type: "error" });
    } finally {
      setBusy(event.currentTarget, false);
    }
  });
}

/* ---------------------------------------------------------------- business */

function renderBusiness(panel, ctx, user) {
  panel.innerHTML = `
    <div class="card">
      <div class="card__head"><div><h2>Business</h2><div class="sub">Shown on the console and to your team</div></div></div>
      <div class="card__body">
        <form id="business-form" novalidate class="stack">
          <div class="field">
            <label for="b-name">Business name</label>
            <input class="input" id="b-name" value="${esc(user.business?.name || "")}">
          </div>
          <div class="field">
            <label for="b-slug">Business ID</label>
            <input class="input" id="b-slug" value="${esc(String(user.business?.id ?? ctx.businessId))}" disabled>
          </div>
        </form>
      </div>
      <div class="card__foot">
        <span class="small dim">Used across orders, payments and analytics.</span>
        <button class="btn btn--primary js-save-business">${icon("check", 15)} Save business</button>
      </div>
    </div>`;

  qs(".js-save-business", panel).addEventListener("click", async (event) => {
    const name = qs("#b-name", panel).value.trim();
    if (!name) {
      toast("Business name cannot be empty", { type: "warn" });
      return;
    }
    setBusy(event.currentTarget, true, "Saving…");
    try {
      const updated = await api.updateBusiness(ctx.businessId, { name });
      toast("Business updated");
      window.dispatchEvent(new CustomEvent("sf:profile-updated", { detail: updated }));
    } catch (error) {
      toast(error.message || "Could not save the business", { type: "error" });
    } finally {
      setBusy(event.currentTarget, false);
    }
  });
}

/* ---------------------------------------------------------------- payments */

async function renderPayments(panel, ctx, user) {
  const accounts = await api.paymentAccounts(ctx.businessId);
  panel.innerHTML = `
    <div class="stack">
      <div class="card">
        <div class="card__head"><div><h2>Receiving account</h2><div class="sub">Default provider and number for this business</div></div></div>
        <div class="card__body">
          <form id="recv-form" novalidate class="form-grid">
            <div class="field">
              <label for="rp-provider">Provider</label>
              <select class="select" id="rp-provider" name="payment_provider">
                ${["bkash", "nagad", "rocket", "upay"]
                  .map((provider) => `<option value="${provider}" ${user.payment_provider === provider ? "selected" : ""}>${esc(providerLabel(provider))}</option>`)
                  .join("")}
              </select>
            </div>
            <div class="field">
              <label for="rp-number">Receiving number</label>
              <input class="input" id="rp-number" name="receiving_number" inputmode="tel" value="${esc(user.receiving_number || "")}" placeholder="01XXXXXXXXX">
            </div>
          </form>
        </div>
        <div class="card__foot">
          <span class="small dim">Saved numbers appear under Payments → Accounts.</span>
          <button class="btn btn--primary js-save-recv">${icon("check", 15)} Save account</button>
        </div>
      </div>
      <div class="card card--flush">
        <div class="card__head"><div><h2>Connected accounts</h2><div class="sub">Payments to these numbers are matched to your orders</div></div></div>
        <div class="card__body">
          ${
            accounts.length
              ? accounts
                  .map(
                    (account) => `
              <div class="provider-row">
                <span class="provider-logo">${providerLogo(account.provider)}</span>
                <div class="grow">
                  <div style="font-weight:600; color:var(--ink)">${esc(providerLabel(account.provider))} · <span class="mono">${esc(account.receiving_number)}</span></div>
                  <div class="small dim">${(account.account_type || "personal") === "merchant" ? "Merchant account" : "Personal number"} · connected ${esc(fmt.date(account.connected_at))}</div>
                </div>
                <span class="badge badge--${(account.account_type || "personal") === "merchant" ? "info" : "slate"}">${(account.account_type || "personal") === "merchant" ? "Merchant" : "Personal"}</span>
                <span class="badge badge--ok">${esc(account.status)}</span>
                <button class="copy-btn js-copy" data-copy="${esc(account.receiving_number)}" aria-label="Copy number">${icon("copy", 14)}</button>
              </div>`
                  )
                  .join("")
              : `<p class="dim small">No accounts connected yet.</p>`
          }
        </div>
      </div>
    </div>`;

  on(panel, "click", ".js-copy", (event, target) => copyText(target.dataset.copy));
  qs(".js-save-recv", panel).addEventListener("click", async (event) => {
    const form = qs("#recv-form", panel);
    clearFieldErrors(form);
    const values = formValues(form);
    if (!values.receiving_number) {
      fieldError(form, "receiving_number", "Enter the receiving number");
      return;
    }
    setBusy(event.currentTarget, true, "Saving…");
    try {
      await api.updateMe({
        payment_provider: values.payment_provider,
        receiving_number: values.receiving_number,
      });
      toast("Receiving account updated");
      await paintPanel(qs("#settings-panel"), ctx);
    } catch (error) {
      toast(error.message || "Could not save the account", { type: "error" });
      setBusy(event.currentTarget, false);
    }
  });
}

/* ---------------------------------------------------------------- security */

function renderSecurity(panel) {
  panel.innerHTML = `
    <div class="card">
      <div class="card__head"><div><h2>Change password</h2><div class="sub">Use at least 4 characters</div></div></div>
      <div class="card__body">
        <form id="pass-form" novalidate class="stack" style="max-width:420px">
          <div class="field">
            <label for="pc-current">Current password</label>
            <input class="input" id="pc-current" name="current_password" type="password" autocomplete="current-password">
          </div>
          <div class="field">
            <label for="pc-new">New password</label>
            <input class="input" id="pc-new" name="new_password" type="password" autocomplete="new-password">
          </div>
          <div class="field">
            <label for="pc-confirm">Confirm new password</label>
            <input class="input" id="pc-confirm" name="confirm_password" type="password" autocomplete="new-password">
          </div>
        </form>
      </div>
      <div class="card__foot">
        <span class="small dim">${icon("shield", 13)} Sessions stay signed in until the token expires.</span>
        <button class="btn btn--primary js-save-pass">${icon("key", 15)} Update password</button>
      </div>
    </div>
    <div class="card" style="margin-top:var(--sp-5)">
      <div class="card__head"><div><h2>Account recovery</h2><div class="sub">What to do if you lose access</div></div></div>
      <div class="card__body">
        <div class="pill-note">${icon("info", 14)} Automated password reset by email is not available in this build — there is no mail delivery integration yet. Until then, recovery is handled manually by the SellFlow team, and your email address is the sign-in identifier.</div>
      </div>
    </div>`;

  qs(".js-save-pass", panel).addEventListener("click", async (event) => {
    const form = qs("#pass-form", panel);
    clearFieldErrors(form);
    const values = formValues(form);
    let valid = true;
    if (!values.current_password) { fieldError(form, "current_password", "Enter your current password"); valid = false; }
    if (!values.new_password || values.new_password.length < 4) { fieldError(form, "new_password", "At least 4 characters"); valid = false; }
    if (values.new_password !== values.confirm_password) { fieldError(form, "confirm_password", "Passwords do not match"); valid = false; }
    if (!valid) return;
    setBusy(event.currentTarget, true, "Updating…");
    try {
      await api.changePasscode(values.current_password, values.new_password);
      toast("Password updated");
      form.reset();
    } catch (error) {
      if (error.status === 401) {
        fieldError(form, "current_password", "Current password is incorrect");
      } else {
        toast(error.message || "Could not update the password", { type: "error" });
      }
    } finally {
      setBusy(event.currentTarget, false);
    }
  });
}

/* ----------------------------------------------------------- notifications */

function renderNotifications(panel) {
  panel.innerHTML = `
    <div class="card">
      <div class="card__head"><div><h2>Notifications</h2><div class="sub">What the platform actually sends today</div></div></div>
      <div class="card__body stack">
        <div class="provider-row">
          <span class="thumb">${icon("link", 15)}</span>
          <div class="grow">
            <div style="font-weight:600; color:var(--ink)">Order events → signed webhooks</div>
            <div class="small dim">When an order is created or its status changes, SellFlow delivers an HMAC-SHA256-signed POST to every active subscription of this business (configured through the webhooks API).</div>
          </div>
          <span class="badge badge--ok">Active</span>
        </div>
        <div class="provider-row">
          <span class="thumb">${icon("alert", 15)}</span>
          <div class="grow">
            <div style="font-weight:600; color:var(--ink)">Payment review queue</div>
            <div class="small dim">Transactions without a confident order match appear under Payments → Needs review, and the Home dashboard shows the current count. Email or push alerts for them are not implemented.</div>
          </div>
          <span class="badge badge--slate">In-console only</span>
        </div>
        <div class="provider-row">
          <span class="thumb">${icon("bell", 15)}</span>
          <div class="grow">
            <div style="font-weight:600; color:var(--ink)">Customer email &amp; SMS updates</div>
            <div class="small dim">Message delivery to your customers is not active in this build — the notification service only logs. No preference switch is shown because a switch would do nothing.</div>
          </div>
          <span class="badge badge--warn">Coming soon</span>
        </div>
      </div>
      <div class="card__foot">
        <span class="small dim">${icon("info", 13)} Preferences will appear here once a real delivery provider is integrated and tested.</span>
      </div>
    </div>`;
}

/* -------------------------------------------------------------------- data */

async function renderData(panel, ctx) {
  panel.innerHTML = `
    <div class="card">
      <div class="card__head"><div><h2>Export your data</h2><div class="sub">Generated in your browser from this business's records only</div></div></div>
      <div class="card__body stack">
        <div class="provider-row">
          <span class="thumb">${icon("receipt", 15)}</span>
          <div class="grow">
            <div style="font-weight:600; color:var(--ink)">Orders</div>
            <div class="small dim">Every order with customer, status, payment state, COD flag and totals.</div>
          </div>
          <button class="btn btn--sm js-export-orders">${icon("download", 14)} CSV</button>
        </div>
        <div class="provider-row">
          <span class="thumb">${icon("wallet", 15)}</span>
          <div class="grow">
            <div style="font-weight:600; color:var(--ink)">Recorded payments</div>
            <div class="small dim">Payments recorded against orders, with method and reference.</div>
          </div>
          <button class="btn btn--sm js-export-payments">${icon("download", 14)} CSV</button>
        </div>
        <div class="provider-row">
          <span class="thumb">${icon("users", 15)}</span>
          <div class="grow">
            <div style="font-weight:600; color:var(--ink)">Customers</div>
            <div class="small dim">Directory with contact details and purchase summaries from real orders.</div>
          </div>
          <button class="btn btn--sm js-export-customers">${icon("download", 14)} CSV</button>
        </div>
      </div>
      <div class="card__foot">
        <span class="small dim">${icon("shield", 13)} Exports contain your business data — store them accordingly. Nothing is uploaded anywhere.</span>
      </div>
    </div>`;

  const stamp = () => new Date().toISOString().slice(0, 10);

  qs(".js-export-orders", panel).addEventListener("click", async (event) => {
    setBusy(event.currentTarget, true, "Preparing…");
    try {
      const orders = await api.orders(ctx.businessId);
      downloadCsv(`sellflow-orders-${stamp()}.csv`, [
        ["order_id", "placed_at", "customer", "customer_phone", "items", "status", "payment_status", "cod", "delivery_fee_bdt", "discount_bdt", "total_bdt"],
        ...orders.map((order) => [
          order.id,
          order.created_at,
          order.customer?.name || "Walk-in",
          order.customer?.phone || "",
          (order.items || []).reduce((sum, item) => sum + item.quantity, 0),
          order.status,
          order.payment_status,
          order.is_cod ? "yes" : "no",
          Number(order.delivery_fee).toFixed(2),
          Number(order.discount).toFixed(2),
          Number(order.total_amount).toFixed(2),
        ]),
      ]);
      toast(`Exported ${orders.length} order${orders.length === 1 ? "" : "s"}`);
    } catch (error) {
      toast(error.message || "Could not build the export", { type: "error" });
    } finally {
      setBusy(event.currentTarget, false);
    }
  });

  qs(".js-export-payments", panel).addEventListener("click", async (event) => {
    setBusy(event.currentTarget, true, "Preparing…");
    try {
      const payments = await api.payments(ctx.businessId);
      downloadCsv(`sellflow-payments-${stamp()}.csv`, [
        ["payment_id", "order_id", "paid_at", "method", "amount_bdt", "transaction_reference", "status"],
        ...payments.map((payment) => [
          payment.id,
          payment.order_id,
          payment.paid_at || payment.created_at,
          payment.method,
          Number(payment.amount).toFixed(2),
          payment.transaction_id || "",
          payment.status,
        ]),
      ]);
      toast(`Exported ${payments.length} payment${payments.length === 1 ? "" : "s"}`);
    } catch (error) {
      toast(error.message || "Could not build the export", { type: "error" });
    } finally {
      setBusy(event.currentTarget, false);
    }
  });

  qs(".js-export-customers", panel).addEventListener("click", async (event) => {
    setBusy(event.currentTarget, true, "Preparing…");
    try {
      const [customers, orders] = await Promise.all([
        api.customers(ctx.businessId),
        api.orders(ctx.businessId),
      ]);
      const totals = new Map();
      for (const order of orders) {
        if (!order.customer_id || order.status === "cancelled") continue;
        const entry = totals.get(order.customer_id) || { count: 0, spent: 0 };
        entry.count += 1;
        entry.spent += Number(order.total_amount || 0);
        totals.set(order.customer_id, entry);
      }
      downloadCsv(`sellflow-customers-${stamp()}.csv`, [
        ["customer_id", "name", "phone", "email", "address", "added_at", "orders_placed", "total_purchased_bdt"],
        ...customers.map((customer) => {
          const stat = totals.get(customer.id) || { count: 0, spent: 0 };
          return [
            customer.id,
            customer.name,
            customer.phone || "",
            customer.email || "",
            customer.address || "",
            customer.created_at,
            stat.count,
            stat.spent.toFixed(2),
          ];
        }),
      ]);
      toast(`Exported ${customers.length} customer${customers.length === 1 ? "" : "s"}`);
    } catch (error) {
      toast(error.message || "Could not build the export", { type: "error" });
    } finally {
      setBusy(event.currentTarget, false);
    }
  });
}

function downloadCsv(filename, rows) {
  const escapeCell = (value) => {
    const text = value == null ? "" : String(value);
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  // The BOM keeps Excel reading the file as UTF-8.
  const csv = "\uFEFF" + rows.map((row) => row.map(escapeCell).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/* -------------------------------------------------------------- appearance */

function renderAppearance(panel) {
  const current = localStorage.getItem("sf.theme") || "system";
  panel.innerHTML = `
    <div class="card">
      <div class="card__head"><div><h2>Appearance</h2><div class="sub">Theme preference for this device</div></div></div>
      <div class="card__body">
        <div class="grid grid-3" id="theme-options">
          ${[
            ["system", "System", "Matches your device", "sliders"],
            ["light", "Light", "Bright surfaces", "sun"],
            ["dark", "Dark", "Deep navy", "moon"],
          ]
            .map(
              ([value, label, sub, iconName]) => `
            <button class="card js-theme ${current === value ? "is-selected" : ""}" data-theme-value="${value}"
              style="text-align:left; cursor:pointer; padding:var(--sp-4); ${current === value ? "border-color:var(--teal-600); box-shadow:var(--ring)" : ""}">
              <div class="row-tight" style="color:var(--teal-ink)">${icon(iconName, 18)} <b>${esc(label)}</b></div>
              <div class="small dim" style="margin-top:6px">${esc(sub)}</div>
            </button>`
            )
            .join("")}
        </div>
      </div>
      <div class="card__foot">
        <span class="small dim">Also available from the top bar.</span>
      </div>
    </div>`;

  qsa(".js-theme", panel).forEach((button) =>
    button.addEventListener("click", () => {
      window.dispatchEvent(
        new CustomEvent("sf:set-theme", { detail: button.dataset.themeValue })
      );
      qsa(".js-theme", panel).forEach((node) => {
        node.classList.remove("is-selected");
        node.style.borderColor = "";
        node.style.boxShadow = "";
      });
      button.classList.add("is-selected");
      button.style.borderColor = "var(--teal-600)";
      button.style.boxShadow = "var(--ring)";
    })
  );
}
