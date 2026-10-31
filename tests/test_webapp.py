"""The web console is served by the API itself (dependency-free static mount).

These tests run under the same guarded suite as everything else
(`tests/conftest.py` refuses non-`*_test` databases).
"""

from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
WEBAPP = BACKEND / "webapp"


def test_webapp_files_exist():
    assert (WEBAPP / "index.html").is_file()
    assert (WEBAPP / "css" / "app.css").is_file()
    for module in ("app.js", "api.js", "ui.js", "charts.js"):
        assert (WEBAPP / "js" / module).is_file(), module
    for page in (
        "auth.js",
        "overview.js",
        "orders.js",
        "payments.js",
        "products.js",
        "customers.js",
        "analytics.js",
        "settings.js",
    ):
        assert (WEBAPP / "js" / "pages" / page).is_file(), page


def test_webapp_index_is_served(client):
    response = client.get("/app/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SellFlow" in response.text


def test_webapp_assets_are_served(client):
    assert client.get("/app/css/app.css").status_code == 200
    assert client.get("/app/js/app.js").status_code == 200
    assert client.get("/app/js/pages/overview.js").status_code == 200


def test_console_redirect(client):
    response = client.get("/console", follow_redirects=False)
    assert response.status_code in (302, 303, 307, 308)
    assert response.headers["location"] == "/app/"


def test_shared_font_assets_are_served(client):
    response = client.get("/assets/fonts/Inter-Regular.ttf")
    assert response.status_code == 200


# --- Public marketing site + PWA --------------------------------------------
#
# The marketing site is a static mount at the repository root, registered LAST
# so /app, /assets, /uploads and the API routers always win. These tests pin
# that ordering and the PWA contract (manifest + service worker policy).

SITE = WEBAPP / "site"


def test_site_files_exist():
    assert (SITE / "index.html").is_file()
    assert (SITE / "site.css").is_file()
    assert (SITE / "site.js").is_file()
    assert (SITE / "manifest.webmanifest").is_file()
    assert (SITE / "sw.js").is_file()
    assert (SITE / "offline.html").is_file()
    assert (SITE / "robots.txt").is_file()
    assert (SITE / "icons" / "favicon.svg").is_file()
    assert (SITE / "icons" / "Icon-192.png").is_file()


def test_root_serves_the_marketing_site(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "Run your social commerce" in body
    # Honest placeholders: no store links and no invented claims.
    assert "Coming soon" in body
    assert "Play Store" in body and "App Store" in body


def test_marketing_site_files_are_served(client):
    for path in (
        "/site.css",
        "/site.js",
        "/manifest.webmanifest",
        "/sw.js",
        "/offline.html",
        "/robots.txt",
        "/icons/favicon.svg",
        "/icons/Icon-192.png",
    ):
        response = client.get(path)
        assert response.status_code == 200, path


def test_api_and_console_win_over_the_root_mount(client):
    """Ordering: concrete mounts and routers must beat the catch-all site."""
    assert client.get("/app/").status_code == 200
    assert "SellFlow" in client.get("/app/").text
    assert client.get("/api/v1/info").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_manifest_is_valid_json_with_pwa_fields(client):
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["name"] and manifest["short_name"]
    assert manifest["start_url"].startswith("/")
    assert manifest["display"] in {"standalone", "minimal-ui", "fullscreen"}
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_service_worker_never_caches_api_or_private_paths(client):
    """Security contract: /api, /uploads and Authorization requests are never cached."""
    source = client.get("/sw.js").text
    assert '"/api/"' in source and '"/uploads/"' in source
    assert 'request.headers.has("authorization")' in source
    # Network-first navigations fall back to the precached offline page.
    assert "/offline.html" in source


def test_sw_precache_list_is_servable(client):
    """Everything the service worker precaches must answer 200 on the live app."""
    for path in (
        "/",
        "/offline.html",
        "/site.css",
        "/site.js",
        "/manifest.webmanifest",
        "/icons/favicon.svg",
        "/icons/Icon-192.png",
        "/icons/Icon-512.png",
        "/app/",
    ):
        assert client.get(path).status_code == 200, path


def test_robots_keeps_private_areas_out_of_crawlers(client):
    body = client.get("/robots.txt").text
    for disallowed in ("/app/", "/api/", "/uploads/"):
        assert f"Disallow: {disallowed}" in body
