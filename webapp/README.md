# SellFlow Web Surfaces

Two dependency-free static surfaces, both served by the FastAPI backend
(no build step, no npm, no bundler — plain ES modules and CSS):

* **Public marketing site + PWA** — `site/`, mounted at **`/`** (index.html,
  `/site.css`, `/site.js`, `/manifest.webmanifest`, `/sw.js`, `/offline.html`,
  `/robots.txt`, `/icons/…`).
* **Seller console** — `webapp/` (this directory), mounted at **`/app/`**
  (`/console` redirects there).

Both import the same design tokens (`css/tokens.css`, served at
`/app/css/tokens.css`), so a token change flows through the whole product.

---

## Marketing site + PWA (`site/`)

| File | Purpose |
| --- | --- |
| `index.html` | Hero, features, how-it-works, payments-honesty, security, Android/iOS “Coming soon” cards, early-access band, FAQ, footer. Login/registration entry points link to `/app/#/login` and `/app/#/register`. |
| `site.css` | Marketing styles; imports `/app/css/tokens.css`. |
| `site.js` | Mobile nav, install prompt (`beforeinstallprompt`), theme sync, service-worker registration. |
| `manifest.webmanifest` | Installable app metadata (icons, shortcuts to Orders/Payments/Products, start at `/app/`). |
| `sw.js` | Precache: site shell, offline page, console shell, icons. Runtime: stale-while-revalidate for `/assets/*`, `/app/css/*`, `/app/js/*`. **Never cached:** `/api/*`, `/uploads/*`, any request with an `Authorization` header — API responses contain private seller data. |
| `offline.html` | Offline fallback for navigations. |
| `robots.txt` | Allows the marketing site; disallows `/app/`, `/api/`, `/uploads/`, `/device-bridge/`, `/payment-accounts/`. |

Honesty rules for site copy (keep them when editing):

* No invented testimonials, counts, revenue figures, certifications or
  integrations.
* Android/iOS downloads stay disabled “Coming soon” buttons until real store
  listings exist. The text states that iOS cannot read incoming SMS by
  platform design.
* Payment wording keeps the statuses distinct (notification received → parsed
  → matched → reconciled → needs review) and never claims provider
  verification that an authorized mechanism has not confirmed.

---

## Seller console (this directory)

## Design system

* **Tokens:** shared `css/tokens.css` (`:root` + `[data-theme="dark"]`),
  imported by `css/app.css`. Change a token, not a component.
* **Typography:** Manrope (display, loaded from Google Fonts with graceful
  fallback) + self-hosted Inter (UI/data) served from `/assets/fonts`.
  Numeric data uses tabular figures (`.num`, `.money`).
* **Color:** deep navy surfaces, teal accent (`--teal-600`), restrained
  gradients (`--grad-navy`, `--grad-teal`). Semantic status colors for
  matched/pending/review/duplicate states.
* **Icons:** inline SVG set with a consistent 1.75 stroke (`js/ui.js`,
  `ICON_PATHS`). No icon font.
* **Charts:** hand-rolled SVG (`js/charts.js`): smooth area chart with hover
  tooltips, donut for payment outcomes, CSS bar lists. Real API data only —
  empty states when there is nothing to show.
* **Motion:** short fades/slides (140–260 ms), fully disabled by
  `prefers-reduced-motion`.
* **Responsive:** desktop sidebar → icon rail (≤1120 px) → bottom navigation
  + drawer (≤760 px); tables transform into stacked cards (≤920 px);
  dialogs become bottom sheets on phones.

## Structure

```
webapp/
├── index.html          # shell, font links, favicon, manifest links
├── _review.html        # local-only visual review harness (credentials via query
│                       #   params; renders the console in iframes at several widths;
│                       #   supports src=<url with %W% width placeholder> for the site)
├── css/
│   ├── tokens.css      # shared design tokens (console + marketing site)
│   └── app.css         # reset + every component (imports tokens.css)
├── js/
│   ├── api.js          # typed API client (same-origin /api/v1)
│   ├── ui.js           # helpers, icons, toasts, modals, skeletons, states
│   ├── charts.js       # SVG charts
│   ├── app.js          # shell, router (hash), theme, session, SW registration
│   └── pages/          # one module per page (auth, overview, orders, products,
│                       #   customers, payments, analytics, settings)
└── site/               # public marketing site + PWA (mounted at /)
```

Primary navigation (exactly six items): **Home, Orders, Products, Customers,
Payments** under “Workspace”, plus **Settings** under “System”; Analytics sits
between them under “Insights”. Mobile tab bar: Home, Orders, Products,
Payments, More.

Use the review harness while iterating on visuals:

```
http://127.0.0.1:8000/app/_review.html?email=<demo>&password=<demo>&theme=light&route=orders&sizes=mobile,tablet,desktop
http://127.0.0.1:8000/app/_review.html?auth=0&sizes=mobile&src=/
```

It is development tooling only: it renders pages in iframes, takes an optional
`click=<selector>` to open a modal, and never stores credentials beyond the
normal session token. Delete it before any public deployment if you prefer.

## Running locally

Both surfaces are served by the API, so start the backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
# marketing site:  http://127.0.0.1:8000/
# seller console:  http://127.0.0.1:8000/app/
```

For a populated local review environment (isolated test database only):

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/sellflow_migration_test"
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

The demo login is printed by the script (`demo@sellflow.app` / `demo1234`) and
includes products (one archived), customers, orders (some COD, some with
courier/tracking), recorded payments, and payment-intelligence events produced
by the real reconciliation engine.

## Conventions for contributors

* Escape **all** interpolated data with `esc()` — pages build HTML strings.
* Add new UI states (loading/empty/error) alongside any new data view.
* Prefer tokens/components over one-off styles; keep focus-visible rings,
  ARIA labels and 44 px touch targets.
* The console talks only to the existing FastAPI endpoints — do not add
  backend coupling beyond `js/api.js`.
* Keep console copy factual: an engine-matched payment is “Matched”, never
  “Verified by the provider”.
