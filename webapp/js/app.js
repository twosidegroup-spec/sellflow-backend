/* SellFlow console — app shell, router, theme. */

import { api } from "./api.js";
import { brandMark, esc, fmt, icon, on, qs, qsa, skeleton, toast } from "./ui.js";
import * as auth from "./pages/auth.js";
import * as overview from "./pages/overview.js";
import * as orders from "./pages/orders.js";
import * as payments from "./pages/payments.js";
import * as products from "./pages/products.js";
import * as customers from "./pages/customers.js";
import * as analytics from "./pages/analytics.js";
import * as settings from "./pages/settings.js";

const ROUTES = {
  overview: { title: "Home", subtitle: "Your business at a glance", render: overview.render, nav: "overview" },
  orders: { title: "Orders", subtitle: "Pipeline and fulfilment", render: orders.render, nav: "orders" },
  payments: { title: "Payments", subtitle: "Reconciliation and accounts", render: payments.render, nav: "payments" },
  products: { title: "Products", subtitle: "Catalogue, pricing and stock", render: products.render, nav: "products" },
  customers: { title: "Customers", subtitle: "Your buyer directory", render: customers.render, nav: "customers" },
  analytics: { title: "Analytics", subtitle: "Performance from recorded orders", render: analytics.render, nav: "analytics" },
  settings: { title: "Settings", subtitle: "Account and configuration", render: settings.render, nav: "settings" },
};

const NAV_GROUPS = [
  {
    label: "Workspace",
    items: [
      ["overview", "Home", "home"],
      ["orders", "Orders", "receipt"],
      ["products", "Products", "box"],
      ["customers", "Customers", "users"],
      ["payments", "Payments", "wallet"],
    ],
  },
  {
    label: "Insights",
    items: [["analytics", "Analytics", "activity"]],
  },
  {
    label: "System",
    items: [["settings", "Settings", "settings"]],
  },
];

const MOBILE_TABS = [
  ["overview", "Home", "home"],
  ["orders", "Orders", "receipt"],
  ["products", "Products", "box"],
  ["payments", "Payments", "wallet"],
  ["more", "More", "menu"],
];

let shellMounted = false;
let reviewCount = 0;
let userMenuOpen = false;

/* ------------------------------------------------------------------ theme */

function resolveTheme(preference) {
  if (preference === "light" || preference === "dark") return preference;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(preference) {
  const resolved = resolveTheme(preference);
  document.documentElement.dataset.theme = resolved;
  const meta = qs('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", resolved === "dark" ? "#070D18" : "#0B1628");
  const toggle = qs(".js-theme-toggle");
  if (toggle) {
    toggle.innerHTML = icon(resolved === "dark" ? "sun" : "moon", 17);
    toggle.title = resolved === "dark" ? "Switch to light theme" : "Switch to dark theme";
  }
}

function initTheme() {
  applyTheme(localStorage.getItem("sf.theme") || "system");
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if ((localStorage.getItem("sf.theme") || "system") === "system") {
      applyTheme("system");
    }
  });
  window.addEventListener("sf:set-theme", (event) => {
    const value = event.detail || "system";
    localStorage.setItem("sf.theme", value);
    applyTheme(value);
  });
}

function toggleTheme() {
  const resolved = document.documentElement.dataset.theme;
  window.dispatchEvent(new CustomEvent("sf:set-theme", { detail: resolved === "dark" ? "light" : "dark" }));
}

/* ------------------------------------------------------------------ shell */

function navItemsHtml(activeNav) {
  return NAV_GROUPS.map(
    (group) => `
    <div class="sidebar__group">
      <div class="sidebar__label">${esc(group.label)}</div>
      <div class="sidebar__nav">
        ${group.items
          .map(
            ([key, label, iconName]) => `
          <a class="nav-item ${activeNav === key ? "is-active" : ""}" href="#/${key === "overview" ? "" : key}" data-nav="${key}">
            ${icon(iconName, 18)}<span class="label">${esc(label)}</span>
            ${key === "payments" ? `<span class="count js-review-count hidden">${reviewCount}</span>` : ""}
          </a>`
          )
          .join("")}
      </div>
    </div>`
  ).join("");
}

function mountShell(activeNav) {
  const app = qs("#app");
  app.ariaBusy = "false";
  app.innerHTML = `
    <div class="shell">
      <aside class="sidebar" aria-label="Primary">
        <div class="sidebar__brand">
          ${brandMark(34)}
          <div class="text">
            <div class="name">SellFlow</div>
            <div class="sub">Console</div>
          </div>
        </div>
        <nav id="sidebar-nav" style="display:flex; flex-direction:column">${navItemsHtml(activeNav)}</nav>
        <div class="sidebar__foot">
          <div class="sidebar__user">
            <span class="avatar" style="background:rgba(24,198,179,.18); color:#2ED3C0" id="sidebar-avatar">?</span>
            <div class="text grow truncate">
              <div class="name truncate" id="sidebar-name">—</div>
              <div class="biz truncate" id="sidebar-biz">—</div>
            </div>
            <button class="icon-btn js-signout-sidebar" style="color:#8DA2C0" title="Sign out" aria-label="Sign out">${icon("logout", 16)}</button>
          </div>
        </div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="topbar__title">
            <h1 id="page-title">—</h1>
            <p id="page-subtitle">—</p>
          </div>
          <div class="topbar__actions">
            <span class="biz-chip" title="Current business"><span class="dot"></span><span id="biz-chip-name">—</span></span>
            <button class="icon-btn js-theme-toggle" title="Toggle theme" aria-label="Toggle light or dark theme">${icon("moon", 17)}</button>
            <div class="menu-wrap">
              <button class="icon-btn js-user-menu" aria-label="Account menu" aria-haspopup="true">${icon("user", 17)}</button>
            </div>
          </div>
        </header>
        <main id="main" class="content" tabindex="-1" aria-live="polite"></main>
      </div>
    </div>
    <nav class="bottom-nav" aria-label="Quick navigation">
      <div class="bottom-nav__items">
        ${MOBILE_TABS.map(
          ([key, label, iconName]) => `
          <button class="bn-item ${activeNav === key ? "is-active" : ""}" data-tab="${key}">
            ${icon(iconName, 21)}<span>${esc(label)}</span>
          </button>`
        ).join("")}
      </div>
    </nav>
    <div class="drawer-scrim js-drawer-close"></div>
    <aside class="drawer" id="drawer" aria-label="Menu">
      <div class="row spread" style="padding:0 10px 14px">
        <div class="row-tight" style="color:#fff">${brandMark(28)}<b style="font-family:var(--font-display)">SellFlow</b></div>
        <button class="icon-btn js-drawer-close" style="color:#8DA2C0" aria-label="Close menu">${icon("x", 17)}</button>
      </div>
      ${navItemsHtml(activeNav)}
      <div style="margin-top:auto; padding-top:16px">
        <button class="nav-item js-signout" style="width:100%">${icon("logout", 18)}<span class="label">Sign out</span></button>
      </div>
    </aside>`;

  shellMounted = true;
  applyTheme(localStorage.getItem("sf.theme") || "system");

  on(app, "click", ".js-theme-toggle", toggleTheme);
  on(app, "click", ".js-signout, .js-signout-sidebar", signOut);
  on(app, "click", ".js-drawer-close", () => document.body.classList.remove("drawer-open"));
  on(app, "click", "[data-tab]", (event, target) => {
    const key = target.dataset.tab;
    if (key === "more") {
      document.body.classList.add("drawer-open");
    } else {
      window.location.hash = key === "overview" ? "#/" : `#/${key}`;
    }
  });
  on(app, "click", ".js-user-menu", (event, target) => {
    event.stopPropagation();
    openUserMenu(target);
  });
}

function refreshShellIdentity() {
  const user = api.user;
  if (!user) return;
  qs("#sidebar-avatar") && (qs("#sidebar-avatar").textContent = fmt.initials(user.full_name));
  qs("#sidebar-name") && (qs("#sidebar-name").textContent = user.full_name);
  qs("#sidebar-biz") && (qs("#sidebar-biz").textContent = user.business?.name || "—");
  qs("#biz-chip-name") && (qs("#biz-chip-name").textContent = user.business?.name || "—");
}

function setActiveNav(activeNav, route) {
  const hash = activeNav === "overview" ? "#/" : `#/${activeNav}`;
  qsa("[data-nav]", document).forEach((node) => {
    node.classList.toggle("is-active", node.dataset.nav === activeNav);
    if (node.getAttribute("href")) node.setAttribute("href", `#/${node.dataset.nav === "overview" ? "" : node.dataset.nav}`);
  });
  qsa("[data-tab]", document).forEach((node) =>
    node.classList.toggle("is-active", node.dataset.tab === activeNav)
  );
  qs("#page-title").textContent = route.title;
  qs("#page-subtitle").textContent = route.subtitle;
  document.title = `${route.title} · SellFlow`;
  document.body.classList.remove("drawer-open");
  void hash;
}

function openUserMenu(anchor) {
  const existing = qs(".js-user-dropdown");
  if (existing) {
    existing.remove();
    userMenuOpen = false;
    return;
  }
  const wrap = qs(".js-user-menu").closest(".menu-wrap");
  const menu = document.createElement("div");
  menu.className = "menu js-user-dropdown";
  menu.innerHTML = `
    <div class="menu__head">
      <div class="name">${esc(api.user?.full_name || "—")}</div>
      <div class="sub truncate">${esc(api.user?.email || "")}</div>
    </div>
    <div class="menu__sep"></div>
    <button class="menu__item" data-go="settings">${icon("settings", 15)} Settings</button>
    <button class="menu__item" data-go="payments">${icon("wallet", 15)} Payments</button>
    <div class="menu__sep"></div>
    <button class="menu__item menu__item--danger js-signout">${icon("logout", 15)} Sign out</button>`;
  wrap.appendChild(menu);
  userMenuOpen = true;
  const close = (event) => {
    if (!menu.contains(event.target) && !anchor.contains(event.target)) {
      menu.remove();
      userMenuOpen = false;
      document.removeEventListener("click", close);
    }
  };
  setTimeout(() => document.addEventListener("click", close), 0);
  menu.addEventListener("click", (event) => {
    const go = event.target.closest("[data-go]");
    if (go) {
      window.location.hash = go.dataset.go === "overview" ? "#/" : `#/${go.dataset.go}`;
      menu.remove();
    }
    if (event.target.closest(".js-signout")) signOut();
  });
}

async function refreshReviewBadge() {
  try {
    const summary = await api.intelligenceSummary(api.businessId);
    reviewCount = Number(summary.review_events || 0);
  } catch {
    reviewCount = 0;
  }
  qsa(".js-review-count").forEach((node) => {
    node.textContent = reviewCount;
    node.classList.toggle("hidden", !reviewCount);
  });
}

function signOut() {
  api.clearSession();
  // Drop any per-tab hand-off state (may contain customer names) so a
  // different account signing in on the same tab never sees it.
  try {
    sessionStorage.clear();
  } catch {
    /* private mode */
  }
  shellMounted = false;
  toast("Signed out", { type: "info" });
  window.location.hash = "#/login";
}

/* ----------------------------------------------------------------- router */

function parseHash() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [pathPart, queryPart] = raw.split("?");
  const path = (pathPart || "").replace(/\/+$/, "");
  const query = Object.fromEntries(new URLSearchParams(queryPart || ""));
  return { path, query };
}

async function renderPage(key, query) {
  const route = ROUTES[key];
  if (!shellMounted) mountShell(key);
  setActiveNav(key, route);
  refreshShellIdentity();
  void refreshReviewBadge();

  const content = qs("#main");
  content.innerHTML = `<div class="grid grid-4">${skeleton.kpis(4)}</div><div class="card card--flush">${skeleton.table(5)}</div>`;
  try {
    await route.render(content, {
      businessId: api.businessId,
      user: api.user,
      query,
      navigate: (hash) => (window.location.hash = hash),
    });
    content.classList.remove("page-enter");
    requestAnimationFrame(() => content.classList.add("page-enter"));
  } catch (error) {
    content.innerHTML = `<div class="card"><div class="state state--error">
      <span class="glyph">${icon("alert", 22)}</span>
      <h2>Could not load this page</h2>
      <p>${esc(error.message || "Unexpected error.")}</p>
      <button class="btn btn--sm js-retry-page">${icon("refresh", 14)} Retry</button>
    </div></div>`;
    qs(".js-retry-page", content).addEventListener("click", () => renderPage(key, query));
  }
}

async function route() {
  const { path, query } = parseHash();

  if (path === "login" || path === "register") {
    if (api.token && api.user) {
      window.location.hash = "#/";
      return;
    }
    shellMounted = false;
    const app = qs("#app");
    if (path === "login") await auth.renderLogin(app);
    else await auth.renderRegister(app);
    document.title = `${path === "login" ? "Sign in" : "Create account"} · SellFlow`;
    return;
  }

  if (!api.token) {
    window.location.hash = "#/login";
    return;
  }
  if (!api.user) {
    try {
      await loadSession();
    } catch {
      api.clearSession();
      window.location.hash = "#/login";
      return;
    }
  }

  const key = path === "" || path === "overview" ? "overview" : path;
  if (!ROUTES[key]) {
    window.location.hash = "#/";
    return;
  }
  await renderPage(key, query);
}

async function loadSession() {
  const me = await api.me();
  api.user = me;
  api.businessId = me.business?.id ?? null;
  if (!api.businessId) {
    toast("This account has no business yet.", { type: "warn" });
    throw new Error("No business on this account.");
  }
}

/* ------------------------------------------------------------------- boot */

async function boot() {
  initTheme();
  window.addEventListener("hashchange", route);
  window.addEventListener("sf:unauthorized", () => {
    if (qs("#app")?.querySelector(".auth")) return;
    api.clearSession();
    shellMounted = false;
    toast("Your session expired. Please sign in again.", { type: "warn" });
    window.location.hash = "#/login";
  });
  // A deliberate password change revokes every session for the user, including
  // this one (token-version bump). Same cleanup, accurate message.
  window.addEventListener("sf:session-revoked", () => {
    api.clearSession();
    shellMounted = false;
    try {
      sessionStorage.clear();
    } catch {
      /* private mode */
    }
    toast("Password updated. Please sign in again.", { type: "info" });
    window.location.hash = "#/login";
  });
  window.addEventListener("sf:profile-updated", async () => {
    try {
      await loadSession();
      refreshShellIdentity();
    } catch {
      /* ignore */
    }
  });

  // PWA: register the shared service worker (static caching only; never /api).
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }

  if (api.token) {
    try {
      await loadSession();
    } catch {
      api.clearSession();
    }
  }
  route();
}

boot();
