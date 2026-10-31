/* SellFlow marketing site — tiny progressive enhancements, no dependencies. */

(function () {
  "use strict";

  /* Theme: honour an explicit console preference, else the system. The
     no-flash part runs inline in <head>; this only syncs on preference change. */
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener?.("change", () => {
    if (!localStorage.getItem("sf.theme")) {
      document.documentElement.dataset.theme = media.matches ? "dark" : "light";
    }
  });

  /* Footer year */
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* Mobile navigation */
  const toggle = document.getElementById("nav-toggle");
  const links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    links.addEventListener("click", (event) => {
      if (event.target.closest("a")) {
        document.body.classList.remove("nav-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* PWA install affordance — only when the browser offers it */
  let installEvent = null;
  const installButton = document.getElementById("install-btn");
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installEvent = event;
    installButton?.classList.remove("hidden");
  });
  installButton?.addEventListener("click", async () => {
    if (!installEvent) return;
    installEvent.prompt();
    const choice = await installEvent.userChoice.catch(() => null);
    installEvent = null;
    if (choice?.outcome === "accepted") installButton.classList.add("hidden");
  });
  window.addEventListener("appinstalled", () => installButton?.classList.add("hidden"));

  /* Service worker — offline shell and static caching only (never /api). */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }
})();
