/* SellFlow console — UI toolkit: helpers, icons, feedback surfaces, states. */

/* ---------------------------------------------------------------- helpers */

export const esc = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

export function el(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}

export const qs = (selector, root = document) => root.querySelector(selector);
export const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

export function on(root, event, selector, handler) {
  root.addEventListener(event, (event_) => {
    const target = event_.target.closest(selector);
    if (target && root.contains(target)) handler(event_, target);
  });
}

export function debounce(fn, wait = 220) {
  let handle;
  return (...args) => {
    clearTimeout(handle);
    handle = setTimeout(() => fn(...args), wait);
  };
}

/* ------------------------------------------------------------------ icons */

const ICON_PATHS = {
  home: "M3 10.5 12 3l9 7.5|M5 9.7V21h14V9.7",
  receipt: "M6 3h12v18l-2.4-1.6L13.2 21l-2.4-1.6L8.4 21 6 19.4V3z|M9.5 8.5h5M9.5 12h5",
  box: "M21 8 12 3 3 8l9 5 9-5z|M3 8v8l9 5 9-5V8|M12 13v8",
  users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2|M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z|M22 21v-2a4 4 0 0 0-3-3.87|M16 3.13a4 4 0 0 1 0 7.75",
  wallet: "M20 7H5a2 2 0 0 1-2-2 2 2 0 0 1 2-2h13v4|M3 5v14a2 2 0 0 0 2 2h16v-6|M16 13h.01|M3 5v0",
  activity: "M3 12h4l3-8 4 16 3-8h4",
  settings: "M4 6h16M4 12h16M4 18h16|M9 6a2 2 0 1 0-4 0 2 2 0 0 0 4 0zM19 12a2 2 0 1 0-4 0 2 2 0 0 0 4 0zM11 18a2 2 0 1 0-4 0 2 2 0 0 0 4 0z",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8|M13.7 21a2 2 0 0 1-3.4 0",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z|m21 21-4.3-4.3",
  plus: "M12 5v14M5 12h14",
  filter: "M4 5h16l-6.5 7.4V19l-3 1.6v-8.2z",
  chevronDown: "m6 9 6 6 6-6",
  chevronLeft: "m15 18-6-6 6-6",
  chevronRight: "m9 18 6-6-6-6",
  x: "M18 6 6 18M6 6l12 12",
  check: "M20 6 9 17l-5-5",
  checkCircle: "M22 11.1V12a10 10 0 1 1-5.9-9.1|M22 4 12 14.1l-3-3",
  xCircle: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z|M15 9l-6 6M9 9l6 6",
  alert: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z|M12 9v4|M12 17h.01",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z|M12 16v-4|M12 8h.01",
  copy: "M8 8h11a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z|M4 16H3a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v1",
  external: "M14 4h6v6|M20 4 10 14|M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5",
  refresh: "M21 12a9 9 0 1 1-2.6-6.4|M21 3v6h-6",
  calendar: "M8 2v4M16 2v4|M3 8h18|M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  phone: "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  link: "M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7|M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7",
  card: "M2 6h20v12H2z|M2 10h20",
  banknote: "M2 7h20v10H2z|M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z|M6 12h.01M18 12h.01",
  arrowUpRight: "M7 17 17 7|M8 7h9v9",
  arrowDownRight: "M7 7l10 10|M17 8v9H8",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4|M16 17l5-5-5-5|M21 12H9",
  menu: "M4 6h16M4 12h16M4 18h16",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z|M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  edit: "M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z",
  trash: "M3 6h18|M8 6V4h8v2|M19 6l-1 15H6L5 6|M10 11v6M14 11v6",
  moreH: "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  image: "M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z|M8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z|m21 15-5-5L5 21",
  truck: "M10 17h4V5H2v12h3|M20 17h2v-3.3L18.7 9H14v8h3|M16.5 19.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM7.5 19.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z|M12 6v6l4 2",
  bank: "M3 21h18|M5 21V9.5L12 4l7 5.5V21|M9 21v-6h6v6",
  inbox: "M22 12h-6l-2 3h-4l-2-3H2|M5.4 5h13.2L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z",
  download: "M12 3v12|M7 10l5 5 5-5|M5 21h14",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z|M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  eyeOff: "M17.9 17.9A10.4 10.4 0 0 1 12 19c-6.5 0-10-7-10-7a18 18 0 0 1 5.1-5.9M9.9 4.2A9.5 9.5 0 0 1 12 4c6.5 0 10 7 10 7a18 18 0 0 1-2.2 3.1M14.1 14.1a3 3 0 1 1-4.2-4.2|M2 2l20 20",
  sparkle: "M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z",
  fileText: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z|M14 2v6h6|M9 13h6M9 17h4",
  percent: "M19 5 5 19|M7 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  key: "M21 2l-2 2m-7.6 7.6a5.5 5.5 0 1 1-7.8 7.8 5.5 5.5 0 0 1 7.8-7.8zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4",
  plug: "M12 22v-5|M9 8V2|M15 8V2|M6 8h12v3a6 6 0 0 1-12 0z",
  sliders: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3|M1 14h6M9 8h6M17 16h6",
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2|M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
};

export function icon(name, size = 18, className = "") {
  const paths = (ICON_PATHS[name] || ICON_PATHS.info).split("|");
  const body = paths
    .map((d) => `<path d="${d}"/>`)
    .join("");
  return `<svg class="${className}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

export function brandMark(size = 34) {
  return `<svg class="mark" width="${size}" height="${size}" viewBox="0 0 32 32" aria-hidden="true">
    <defs><linearGradient id="bm-${size}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#18C6B4"/><stop offset="1" stop-color="#0E8F84"/>
    </linearGradient></defs>
    <rect width="32" height="32" rx="9" fill="url(#bm-${size})"/>
    <path d="M10 21c0-3.2 2.6-4.4 6-5s6-1.4 6-4.4C22 9.2 19.4 8 16 8s-6 1.2-6 3.6" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M22 11c0 3.2-2.6 4.4-6 5s-6 1.4-6 4.4C10 22.8 12.6 24 16 24s6-1.2 6-3.6" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" opacity=".55"/>
  </svg>`;
}

/* ------------------------------------------------------------- formatters */

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const decimalFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const fmt = {
  money(value, { decimals = false } = {}) {
    const number = Number(value ?? 0);
    if (Number.isNaN(number)) return "—";
    const formatted = decimals ? decimalFormat.format(number) : numberFormat.format(number);
    return `৳${formatted}`;
  },
  moneyExact(value) {
    return this.money(value, { decimals: true });
  },
  num(value) {
    const number = Number(value ?? 0);
    return Number.isNaN(number) ? "—" : numberFormat.format(number);
  },
  pct(value, digits = 1) {
    const number = Number(value ?? 0) * 100;
    return `${number.toFixed(digits)}%`;
  },
  date(value) {
    if (!value) return "—";
    const date = new Date(value);
    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  },
  dateTime(value) {
    if (!value) return "—";
    const date = new Date(value);
    return `${this.date(value)} · ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
  },
  time(value) {
    if (!value) return "—";
    return new Date(value).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  },
  relative(value) {
    if (!value) return "—";
    const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000);
    if (Number.isNaN(seconds)) return "—";
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return this.date(value);
  },
  initials(name) {
    return String(name || "?")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join("");
  },
  maskPhone(value) {
    const digits = String(value || "").replace(/\D/g, "");
    return digits.length > 4 ? `•••• ${digits.slice(-4)}` : "••••";
  },
  titleCase(value) {
    return String(value || "").replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  },
};

const PROVIDER_LABELS = {
  bkash: "bKash",
  nagad: "Nagad",
  rocket: "Rocket",
  upay: "Upay",
  paypal: "PayPal",
  cashapp: "Cash App",
  stripe: "Stripe",
  wise: "Wise",
  cash: "Cash",
  bank: "Bank",
  other: "Other",
};

export function providerLabel(provider) {
  const key = String(provider || "").toLowerCase();
  return PROVIDER_LABELS[key] || fmt.titleCase(key);
}

/* -------------------------------------------------------- status mappings */

export function orderStatusBadge(status) {
  const map = {
    created: ["New", "info"],
    confirmed: ["Confirmed", "violet"],
    packed: ["Packed", "slate"],
    shipped: ["Shipped", "warn"],
    delivered: ["Delivered", "ok"],
    cancelled: ["Cancelled", "danger"],
  };
  const [label, tone] = map[status] || [fmt.titleCase(status), "slate"];
  return `<span class="badge badge--${tone}">${esc(label)}</span>`;
}

export function paymentStateBadge(paymentStatus) {
  const map = {
    paid: ["Paid", "ok"],
    partially_paid: ["Partial", "warn"],
    pending: ["Unpaid", "slate"],
  };
  const [label, tone] = map[paymentStatus] || [fmt.titleCase(paymentStatus || "pending"), "slate"];
  return `<span class="badge badge--${tone}">${esc(label)}</span>`;
}

export function recordedPaymentBadge(status) {
  // These are payments a seller recorded by hand (or through the purchase
  // flow). "Recorded" is the honest label: nothing here is provider-attested.
  const map = {
    verified: ["Recorded", "ok"],
    pending: ["Pending", "warn"],
    failed: ["Failed", "danger"],
    refunded: ["Refunded", "info"],
  };
  const [label, tone] = map[status] || [fmt.titleCase(status), "slate"];
  return `<span class="badge badge--${tone}">${esc(label)}</span>`;
}

export function eventBadge(event) {
  const verification = event.verification_status;
  // "verified" here is the engine's PAID state: the event was parsed and
  // matched to an order. It is not a claim of provider attestation, so the
  // visible label stays factual.
  if (verification === "verified") return `<span class="badge badge--ok">Matched</span>`;
  if (verification === "duplicate") return `<span class="badge badge--slate">Duplicate</span>`;
  if (verification === "rejected") return `<span class="badge badge--danger">Rejected</span>`;
  if (verification === "refunded") return `<span class="badge badge--info">Refunded</span>`;
  if (event.status === "PARTIALLY_PAID") return `<span class="badge badge--warn">Partial</span>`;
  if (event.status === "OVERPAYMENT") return `<span class="badge badge--violet">Overpaid</span>`;
  return `<span class="badge badge--warn">Review</span>`;
}

export function decisionChip(event) {
  if (!event.decision) return "";
  const labels = {
    AUTO_MATCHED: "Auto-matched",
    PARTIALLY_PAID: "Partially paid",
    REQUIRES_REVIEW: "Requires review",
    DUPLICATE_DETECTED: "Duplicate detected",
    UNKNOWN_TRANSACTION: "No confident match",
    AMOUNT_MISMATCH: "Amount mismatch",
    OVERPAYMENT: "Overpayment",
  };
  return `<span class="reason-tag">${esc(labels[event.decision] || event.decision)}</span>`;
}

/* ------------------------------------------------------------------ toasts */

export function toast(message, { type = "success", title = "" } = {}) {
  const region = document.getElementById("toast-region");
  const icons = { success: "checkCircle", error: "xCircle", warn: "alert", info: "info" };
  const node = el(`
    <div class="toast toast--${type}" role="status">
      <span class="icon icon--${type === "success" ? "ok" : type}">${icon(icons[type] || "info", 17)}</span>
      <div class="msg">${title ? `<b>${esc(title)}</b> ` : ""}${esc(message)}</div>
      <button class="icon-btn" style="width:26px;height:26px" aria-label="Dismiss">${icon("x", 14)}</button>
    </div>`);
  const dismiss = () => {
    if (!node.isConnected) return;
    node.classList.add("is-out");
    setTimeout(() => node.remove(), 180);
  };
  qs("button", node).addEventListener("click", dismiss);
  region.appendChild(node);
  setTimeout(dismiss, type === "error" ? 6500 : 4200);
  return dismiss;
}

/* -------------------------------------------------------- modal & confirm */

export function openModal({ title, body, footer = "", wide = false, onMount }) {
  const root = document.getElementById("modal-root");
  const scrim = el(`
    <div class="modal-scrim" role="presentation">
      <div class="modal ${wide ? "modal--wide" : ""}" role="dialog" aria-modal="true" aria-label="${esc(title)}">
        <div class="modal__head">
          <h2>${esc(title)}</h2>
          <button class="icon-btn js-close" aria-label="Close dialog">${icon("x", 17)}</button>
        </div>
        <div class="modal__body"></div>
        ${footer ? `<div class="modal__foot">${footer}</div>` : ""}
      </div>
    </div>`);
  const bodyEl = qs(".modal__body", scrim);
  if (typeof body === "string") bodyEl.innerHTML = body;
  else bodyEl.appendChild(body);

  const close = () => {
    scrim.remove();
    document.removeEventListener("keydown", onKey);
    if (previousFocus?.isConnected) previousFocus.focus();
  };
  const previousFocus = document.activeElement;

  scrim.addEventListener("mousedown", (event_) => {
    if (event_.target === scrim) close();
  });
  qs(".js-close", scrim).addEventListener("click", close);
  qsa("[data-close-modal]", scrim).forEach((btn) => btn.addEventListener("click", close));

  function onKey(event_) {
    if (event_.key === "Escape") {
      event_.stopPropagation();
      close();
      return;
    }
    if (event_.key !== "Tab") return;
    const focusables = qsa(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      scrim
    ).filter((node_) => !node_.disabled && node_.offsetParent !== null);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event_.shiftKey && document.activeElement === first) {
      event_.preventDefault();
      last.focus();
    } else if (!event_.shiftKey && document.activeElement === last) {
      event_.preventDefault();
      first.focus();
    }
  }

  document.addEventListener("keydown", onKey);
  root.appendChild(scrim);
  const autofocus = qs("[autofocus], input, select, textarea", scrim);
  autofocus?.focus();
  onMount?.({ root: scrim, body: bodyEl, close });
  return { root: scrim, body: bodyEl, close };
}

export function confirmDialog({
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  danger = false,
  focusConfirm = false,
}) {
  return new Promise((resolve) => {
    const { root, close } = openModal({
      title,
      body: `
        <div class="row" style="align-items:flex-start; gap:14px">
          <span class="confirm-icon ${danger ? "confirm-icon--danger" : "confirm-icon--warn"}">
            ${icon(danger ? "alert" : "info", 20)}
          </span>
          <p style="color:var(--text); font-size:var(--fs-14); line-height:1.6">${esc(message)}</p>
        </div>`,
      footer: `
        <button class="btn" data-close-modal>${esc(cancelText)}</button>
        <button class="btn ${danger ? "btn--danger" : "btn--primary"} js-confirm">${esc(confirmText)}</button>`,
    });
    const confirmButton = qs(".js-confirm", root);
    if (focusConfirm) confirmButton.focus();
    confirmButton.addEventListener("click", () => {
      close();
      resolve(true);
    });
    root.addEventListener("click", (event_) => {
      if (event_.target === root || event_.target.closest("[data-close-modal]")) {
        queueMicrotask(() => resolve(false));
      }
    });
    const observer = new MutationObserver(() => {
      if (!root.isConnected) {
        observer.disconnect();
        resolve(false);
      }
    });
    observer.observe(document.getElementById("modal-root"), { childList: true });
  });
}

/* --------------------------------------------------------------- skeletons */

export const skeleton = {
  kpis(count = 4) {
    return Array.from({ length: count })
      .map(
        () => `
        <div class="card kpi">
          <div class="skel skel--text" style="width:42%"></div>
          <div class="skel skel--kpi" style="margin-top:14px"></div>
          <div class="skel skel--text" style="width:64%; margin-top:14px"></div>
        </div>`
      )
      .join("");
  },
  table(rows = 6) {
    return `
      <div style="padding:8px 20px 20px">
        ${Array.from({ length: rows })
          .map(() => `<div class="skel skel--row" style="margin-top:12px"></div>`)
          .join("")}
      </div>`;
  },
  chart(height = 220) {
    return `<div class="skel skel--chart" style="height:${height}px"></div>`;
  },
  cards(count = 3) {
    return Array.from({ length: count })
      .map(() => `<div class="skel skel--card"></div>`)
      .join("");
  },
};

/* ------------------------------------------------------------------ states */

export function emptyState({ iconName = "inbox", title, message, action = "" }) {
  return `
    <div class="state">
      <span class="glyph">${icon(iconName, 22)}</span>
      <h2>${esc(title)}</h2>
      ${message ? `<p>${esc(message)}</p>` : ""}
      ${action}
    </div>`;
}

export function errorState(message, retrySelector = ".js-retry") {
  return `
    <div class="state state--error">
      <span class="glyph">${icon("alert", 22)}</span>
      <h2>Something went wrong</h2>
      <p>${esc(message || "The request could not be completed.")}</p>
      <button class="btn btn--sm ${retrySelector.replace(".", "")}" type="button">
        ${icon("refresh", 14)} Try again
      </button>
    </div>`;
}

export function pageLoadError(container, message) {
  container.innerHTML = `<div class="card">${errorState(message)}</div>`;
  qs(".js-retry", container)?.addEventListener("click", () => {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

/* -------------------------------------------------------------- form utils */

export function formValues(form) {
  const values = {};
  qsa("input[name], select[name], textarea[name]", form).forEach((input) => {
    if (input.type === "checkbox") values[input.name] = input.checked;
    else values[input.name] = input.value.trim();
  });
  return values;
}

export function fieldError(form, name, message) {
  const input = qs(`[name="${name}"]`, form);
  if (!input) return;
  input.classList.add("is-invalid");
  let hint = input.closest(".field")?.querySelector(".error");
  if (!hint) {
    hint = el(`<span class="error">${icon("alert", 12)}<span></span></span>`);
    input.closest(".field")?.appendChild(hint);
  }
  qs("span:last-child", hint).textContent = message;
}

export function clearFieldErrors(form) {
  qsa(".is-invalid", form).forEach((node) => node.classList.remove("is-invalid"));
  qsa(".field .error", form).forEach((node) => node.remove());
}

export function setBusy(button, busy, label = "Working…") {
  if (!button) return;
  button.disabled = busy;
  if (busy) {
    button.dataset.label = button.innerHTML;
    button.innerHTML = `<span class="spinner"></span> ${esc(label)}`;
    button.classList.add("is-busy");
  } else if (button.dataset.label) {
    button.innerHTML = button.dataset.label;
    delete button.dataset.label;
    button.classList.remove("is-busy");
  }
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard");
  } catch {
    toast("Could not copy to the clipboard", { type: "warn" });
  }
}

export function sourceIcon(sourceType) {
  if (sourceType === "sms") return "phone";
  if (sourceType === "api") return "plug";
  if (sourceType === "manual") return "edit";
  return "fileText";
}
