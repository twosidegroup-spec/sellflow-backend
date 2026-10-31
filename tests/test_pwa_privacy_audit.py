"""Pre-production acceptance audit — PWA caching and data privacy.

The service worker and the HTTP layer must never let private seller data
survive in a cache that outlives the session or crosses accounts:

* the service worker precaches shells/assets only (never /api, /uploads or
  Authorization-bearing requests)
* the runtime cache prefixes cover static assets only
* API responses are marked `Cache-Control: no-store` so the browser HTTP
  cache cannot replay them to a different account on the same device
* cache invalidation on version bumps is implemented
* the console shell carries no embedded secrets
* the manifest's start_url actually serves the console
"""

from __future__ import annotations

import re

from tests.conftest import register_seller


def _sw_source(client) -> str:
    response = client.get("/sw.js")
    assert response.status_code == 200
    return response.text


def test_service_worker_precache_contains_no_private_paths(client):
    source = _sw_source(client)
    block = re.search(r"const PRECACHE = \[(.*?)\];", source, re.S)
    assert block, "PRECACHE list not found"
    entries = re.findall(r'"([^"]+)"', block.group(1))
    assert entries, entries
    for entry in entries:
        assert not entry.startswith("/api"), entry
        assert not entry.startswith("/uploads"), entry
    # Every precached URL must be servable right now.
    for entry in entries:
        assert client.get(entry).status_code == 200, entry


def test_service_worker_runtime_cache_is_static_only(client):
    source = _sw_source(client)
    block = re.search(r"const RUNTIME_PREFIXES = \[(.*?)\];", source, re.S)
    assert block
    prefixes = re.findall(r'"([^"]+)"', block.group(1))
    assert set(prefixes) == {"/assets/", "/app/css/", "/app/js/"}
    for prefix in prefixes:
        assert not prefix.startswith("/api")


def test_service_worker_private_guard_and_purge_present(client):
    source = _sw_source(client)
    assert 'url.pathname.startsWith("/api/")' in source
    assert 'url.pathname.startsWith("/uploads/")' in source
    assert 'request.headers.has("authorization")' in source
    # Version bump purges older caches on activate.
    assert "caches.delete" in source
    assert 'key.startsWith(VERSION)' in source


def test_api_responses_are_no_store_but_static_files_are_not(client):
    public = client.get("/api/v1/info")
    assert public.status_code == 200
    assert public.headers.get("cache-control") == "no-store"
    assert public.headers.get("x-content-type-options") == "nosniff"

    seller = register_seller(client)
    private = client.get("/api/v1/auth/me", headers=seller["auth"])
    assert private.status_code == 200
    assert private.headers.get("cache-control") == "no-store"
    assert private.json()["email"] == seller["email"]

    static = client.get("/site.css")
    assert static.status_code == 200
    assert static.headers.get("cache-control") != "no-store"


def test_console_shell_carries_no_embedded_secrets(client):
    shell = client.get("/app/")
    assert shell.status_code == 200
    body = shell.text
    assert "sf.token" not in body or "localStorage" in body  # JS reference only
    for needle in ("SECRET_KEY", "DATABASE_URL", "DEVICE_TOKEN_SECRET", "postgresql"):
        assert needle not in body, needle
    # PWA wiring is present on the console shell.
    assert "manifest.webmanifest" in body
    assert "apple-touch-icon" in body


def test_signout_clears_both_session_channels(client):
    """Source-level check: sign-out must drop the token and per-tab state."""
    source = client.get("/app/js/app.js").text
    signout = re.search(r"function signOut\(\) \{(.*?)\n\}", source, re.S)
    assert signout, "signOut not found"
    body = signout.group(1)
    assert "api.clearSession()" in body
    assert "sessionStorage.clear()" in body

    api_source = client.get("/app/js/api.js").text
    assert "localStorage.removeItem(TOKEN_KEY)" in api_source


def test_manifest_start_url_serves_the_console(client):
    manifest = client.get("/manifest.webmanifest").json()
    start = manifest["start_url"].split("#")[0]
    response = client.get(start)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SellFlow" in response.text
