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
