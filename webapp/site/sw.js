/* SellFlow service worker.
 *
 * Policy (deliberate, security-first):
 *   - PRECACHE: the marketing shell, the offline page, the dashboard shell
 *     (static HTML/CSS/JS only — no data) and the app icons.
 *   - RUNTIME: stale-while-revalidate for same-origin static assets
 *     (/assets/*, /app/css/*, /app/js/*).
 *   - NEVER cached: anything under /api/, /uploads/ or with an Authorization
 *     header. API responses contain private seller data.
 *   - Navigations: network-first; if offline, serve the cached shell when it
 *     is one of the precached pages, otherwise the offline page.
 */

const VERSION = "sellflow-v1";
const PRECACHE = [
  "/",
  "/offline.html",
  "/site.css",
  "/site.js",
  "/manifest.webmanifest",
  "/icons/favicon.svg",
  "/icons/Icon-192.png",
  "/icons/Icon-512.png",
  "/app/",
];

const RUNTIME_PREFIXES = ["/assets/", "/app/css/", "/app/js/"];
const RUNTIME_CACHE = `${VERSION}-runtime`;

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(VERSION);
      // Individually, so one missing file cannot fail the whole install.
      await Promise.all(PRECACHE.map((url) => cache.add(url).catch(() => {})));
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })()
  );
});

function isPrivateRequest(request) {
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return true;
  if (url.pathname.startsWith("/api/")) return true;
  if (url.pathname.startsWith("/uploads/")) return true;
  if (request.headers.has("authorization")) return true;
  return false;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  if (isPrivateRequest(request)) return; // straight to the network; never stored

  const url = new URL(request.url);

  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          return await fetch(request);
        } catch {
          const cache = await caches.open(VERSION);
          const shell =
            (await cache.match(url.pathname)) ||
            (await cache.match("/offline.html"));
          return shell || Response.error();
        }
      })()
    );
    return;
  }

  if (RUNTIME_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(RUNTIME_CACHE);
        const cached = await cache.match(request);
        const network = fetch(request)
          .then((response) => {
            if (response.ok) cache.put(request, response.clone());
            return response;
          })
          .catch(() => cached);
        return cached || network;
      })()
    );
  }
});
