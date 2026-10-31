# SellFlow Web Console

A dependency-free web console for SellFlow, served by the FastAPI backend at
**`/app/`** (`/console` redirects there). No build step, no npm, no bundler:
plain ES modules and one stylesheet.

## Design system

* **Tokens:** all colors, type, spacing, radius, elevation and motion live in
  `css/app.css` section 02 (`:root` and `[data-theme="dark"]`). Change a token,
  not a component.
* **Typography:** Manrope (display, loaded from Google Fonts with graceful
  fallback) + self-hosted Inter (UI/data) served from `/assets/fonts`.
  Numeric data uses tabular figures (`.num`, `.money`).
* **Color:** deep navy surfaces, teal accent (`--teal-600`), restrained
  gradients (`--grad-navy`, `--grad-teal`). Semantic status colors for
  verified/pending/review/duplicate states.
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
├── index.html          # shell, font links, favicon
├── _review.html        # local-only visual review harness (credentials via query
│                       #   params; renders the console in iframes at several widths)
├── css/app.css         # design tokens + every component (23 sections)
└── js/
    ├── api.js          # typed API client (same-origin /api/v1)
    ├── ui.js           # helpers, icons, toasts, modals, skeletons, states
    ├── charts.js       # SVG charts
    ├── app.js          # shell, router (hash), theme, session
    └── pages/          # one module per page (auth, overview, orders, …)
```

Use the review harness while iterating on visuals:

```
http://127.0.0.1:8000/app/_review.html?email=<demo>&password=<demo>&theme=light&route=orders&sizes=mobile,tablet,desktop
```

It is development tooling only: it renders the console in iframes, takes an
optional `click=<selector>` to open a modal, and never stores credentials
beyond the normal session token. Delete it before any public deployment if you
prefer.

## Running locally

The console is served by the API, so start the backend and open `/app/`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
# then open http://127.0.0.1:8000/app/
```

For a populated local review environment (isolated test database only):

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/sellflow_migration_test"
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

## Conventions for contributors

* Escape **all** interpolated data with `esc()` — pages build HTML strings.
* Add new UI states (loading/empty/error) alongside any new data view.
* Prefer tokens/components over one-off styles; keep focus-visible rings,
  ARIA labels and 44 px touch targets.
* The console talks only to the existing FastAPI endpoints — do not add
  backend coupling beyond `js/api.js`.
