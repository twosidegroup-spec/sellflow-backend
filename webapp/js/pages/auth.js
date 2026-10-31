/* Auth pages — sign in and create account (split premium layout). */

import { api, ApiError } from "../api.js";
import {
  brandMark,
  clearFieldErrors,
  el,
  esc,
  fieldError,
  formValues,
  icon,
  qs,
  setBusy,
  toast,
} from "../ui.js";

function shell({ mode }) {
  return `
  <div class="auth">
    <aside class="auth__aside">
      <div class="auth__brand">${brandMark(36)}<span class="name">SellFlow</span></div>
      <div class="auth__pitch">
        <h2>Social commerce operations, settled.</h2>
        <p>One console for orders, payments, products and reconciliation — built for sellers in Bangladesh.</p>
        <div class="auth__points">
          <div class="auth__point"><span class="tick">${icon("check", 12)}</span> Track every order from confirmation to delivery</div>
          <div class="auth__point"><span class="tick">${icon("check", 12)}</span> Match bKash payments to orders automatically</div>
          <div class="auth__point"><span class="tick">${icon("check", 12)}</span> Review queue for anything that needs a human decision</div>
        </div>
      </div>
      <div class="auth__meta">© ${new Date().getFullYear()} Two Side Group · SellFlow</div>
    </aside>
    <main class="auth__panel" id="main" tabindex="-1">
      <div class="auth-card">
        <div class="auth-card__head">
          <h1>${mode === "login" ? "Welcome back" : "Create your business account"}</h1>
          <p>${mode === "login" ? "Sign in to your operations console." : "Set up SellFlow for your shop in under a minute."}</p>
        </div>
        <div class="card"><div class="card__body" id="auth-form-body"></div></div>
        <div class="auth-alt" id="auth-alt"></div>
      </div>
    </main>
  </div>`;
}

const providerOptions = ["bkash", "nagad", "rocket", "upay"]
  .map((provider) => `<option value="${provider}">${esc(provider === "bkash" ? "bKash" : provider[0].toUpperCase() + provider.slice(1))}</option>`)
  .join("");

export async function renderLogin(root) {
  root.innerHTML = shell({ mode: "login" });
  root.classList.add("page-enter");
  qs("#auth-alt", root).innerHTML = `New to SellFlow? <a href="#/register">Create a business account</a>`;
  const body = qs("#auth-form-body", root);
  body.innerHTML = `
    <form novalidate>
      <div class="stack">
        <div class="field">
          <label for="email">Email</label>
          <input class="input" id="email" name="email" type="email" autocomplete="email" placeholder="you@example.com" autofocus>
        </div>
        <div class="field">
          <label for="password">Password</label>
          <div class="input-group">
            ${icon("key", 16)}
            <input class="input" id="password" name="password" type="password" autocomplete="current-password" placeholder="Your password">
            <button type="button" class="input-action js-toggle-pw" aria-label="Show password">${icon("eye", 16)}</button>
          </div>
        </div>
        <button class="btn btn--primary" type="submit" style="width:100%; min-height:44px">
          Sign in ${icon("arrowUpRight", 16)}
        </button>
      </div>
    </form>`;

  const form = qs("form", body);
  const toggle = qs(".js-toggle-pw", body);
  toggle.addEventListener("click", () => {
    const input = qs("#password", body);
    const hidden = input.type === "password";
    input.type = hidden ? "text" : "password";
    toggle.innerHTML = icon(hidden ? "eyeOff" : "eye", 16);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFieldErrors(form);
    const values = formValues(form);
    let valid = true;
    if (!values.email) { fieldError(form, "email", "Enter your email"); valid = false; }
    if (!values.password) { fieldError(form, "password", "Enter your password"); valid = false; }
    if (!valid) return;
    const submit = qs('button[type="submit"]', form);
    setBusy(submit, true, "Signing in…");
    try {
      const token = await api.login(values.email, values.password);
      api.setToken(token.access_token);
      await api.me();
      window.location.hash = "#/";
    } catch (error) {
      setBusy(submit, false);
      if (error instanceof ApiError && error.status === 401) {
        fieldError(form, "password", "Incorrect email or password");
        formValues(form);
      } else if (error instanceof ApiError && error.status === 429) {
        toast("Too many attempts. Wait a moment and try again.", { type: "warn", title: "Rate limited" });
      } else {
        toast(error.message || "Sign-in failed", { type: "error" });
      }
    }
  });
}

export async function renderRegister(root) {
  root.innerHTML = shell({ mode: "register" });
  root.classList.add("page-enter");
  qs("#auth-alt", root).innerHTML = `Already have an account? <a href="#/login">Sign in</a>`;
  const body = qs("#auth-form-body", root);
  body.innerHTML = `
    <form novalidate>
      <div class="stack">
        <div class="form-grid">
          <div class="field">
            <label for="full_name">Your name</label>
            <input class="input" id="full_name" name="full_name" autocomplete="name" placeholder="Rahim Uddin">
          </div>
          <div class="field">
            <label for="business_name">Business name</label>
            <input class="input" id="business_name" name="business_name" placeholder="Dhaka Fashion House">
          </div>
          <div class="field">
            <label for="email">Email</label>
            <input class="input" id="email" name="email" type="email" autocomplete="email" placeholder="you@example.com">
          </div>
          <div class="field">
            <label for="phone">Phone</label>
            <input class="input" id="phone" name="phone" inputmode="tel" placeholder="01XXXXXXXXX">
          </div>
          <div class="field">
            <label for="payment_provider">Receiving provider</label>
            <select class="select" id="payment_provider" name="payment_provider">${providerOptions}</select>
          </div>
          <div class="field">
            <label for="receiving_number">Receiving number</label>
            <input class="input" id="receiving_number" name="receiving_number" inputmode="tel" placeholder="01XXXXXXXXX">
            <span class="hint">Payments to this number can be matched to your orders.</span>
          </div>
          <div class="field span-2">
            <label for="password">Password</label>
            <div class="input-group">
              ${icon("key", 16)}
              <input class="input" id="password" name="password" type="password" autocomplete="new-password" placeholder="At least 4 characters">
              <button type="button" class="input-action js-toggle-pw" aria-label="Show password">${icon("eye", 16)}</button>
            </div>
          </div>
        </div>
        <button class="btn btn--primary" type="submit" style="width:100%; min-height:44px">
          Create account ${icon("arrowUpRight", 16)}
        </button>
        <p class="small dim">By creating an account you agree that payment data may be stored to reconcile your orders.</p>
      </div>
    </form>`;

  const form = qs("form", body);
  const toggle = qs(".js-toggle-pw", body);
  toggle.addEventListener("click", () => {
    const input = qs("#password", body);
    const hidden = input.type === "password";
    input.type = hidden ? "text" : "password";
    toggle.innerHTML = icon(hidden ? "eyeOff" : "eye", 16);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFieldErrors(form);
    const values = formValues(form);
    let valid = true;
    if (!values.full_name) { fieldError(form, "full_name", "Enter your name"); valid = false; }
    if (!values.business_name) { fieldError(form, "business_name", "Enter your business name"); valid = false; }
    if (!values.email || !/.+@.+\..+/.test(values.email)) { fieldError(form, "email", "Enter a valid email"); valid = false; }
    if (!values.password || values.password.length < 4) { fieldError(form, "password", "At least 4 characters"); valid = false; }
    if (values.receiving_number && !/^(\+?88)?01[3-9]\d{8}$/.test(values.receiving_number.replace(/[\s-]/g, ""))) {
      fieldError(form, "receiving_number", "Enter a Bangladeshi mobile number");
      valid = false;
    }
    if (!valid) return;

    const submit = qs('button[type="submit"]', form);
    setBusy(submit, true, "Creating account…");
    try {
      await api.register({
        email: values.email,
        full_name: values.full_name,
        password: values.password,
        business_name: values.business_name,
        phone: values.phone || undefined,
        payment_provider: values.payment_provider || undefined,
        receiving_number: values.receiving_number || undefined,
      });
      const token = await api.login(values.email, values.password);
      api.setToken(token.access_token);
      await api.me();
      toast("Business account created", { title: "Welcome to SellFlow" });
      window.location.hash = "#/";
    } catch (error) {
      setBusy(submit, false);
      if (error instanceof ApiError && /already registered/i.test(error.message)) {
        fieldError(form, "email", "That email is already registered — sign in instead");
      } else {
        toast(error.message || "Registration failed", { type: "error" });
      }
    }
  });
}
