"""Regression suite — durable product-image storage (local + Cloudflare R2).

The R2 backend is exercised with a fake S3 client: real-credential verification
against Cloudflare is **BLOCKED** until R2 credentials are provisioned, and is
never faked as successful. Covered here:

* adapter behaviour (save / delete / URL parsing / traversal safety)
* R2 request shape (bucket, key prefix, content type, returned URL)
* storage failures -> 502, generic message, nothing persisted
* oversized and invalid uploads rejected before storage
* product deletion cleans the stored object (best effort)
* deterministic backend selection + fail-closed configuration
* tenant authorization on the upload route
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.storage import (
    LocalStorage,
    R2Storage,
    StorageError,
    get_storage,
    reset_storage_cache,
)
from tests.conftest import register_seller

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae42"
    "6082"
)


@pytest.fixture(autouse=True)
def _fresh_storage_cache():
    """Keep the module-level storage cache deterministic across tests."""
    reset_storage_cache()
    yield
    reset_storage_cache()


# ---------------------------------------------------------------- adapters


def test_local_storage_round_trip(tmp_path):
    storage = LocalStorage(str(tmp_path))
    url = storage.save("biz_1_rnd_photo.png", PNG, "image/png")
    assert url == "/uploads/biz_1_rnd_photo.png"
    assert (tmp_path / "biz_1_rnd_photo.png").read_bytes() == PNG

    assert storage.delete_url(url) is True
    assert not (tmp_path / "biz_1_rnd_photo.png").exists()
    assert storage.delete_url(url) is False  # already gone


def test_local_storage_rejects_unsafe_or_invalid_urls(tmp_path):
    storage = LocalStorage(str(tmp_path))
    secret = tmp_path / "secret.txt"
    secret.write_text("keep me")

    # Traversal attempts never escape the storage directory.
    assert storage.delete_url("/uploads/../../secret.txt") is False
    assert secret.exists()
    assert storage.delete_url("../../secret.txt") is False
    assert secret.exists()
    # Percent-encoded traversal and empty names are not valid filenames.
    assert storage.delete_url("/uploads/..%2F..%2Fetc%2Fpasswd") is False
    assert storage.delete_url("") is False
    assert storage.delete_url(None) is False


class _FakeS3Client:
    def __init__(self, fail_on_put: bool = False):
        self.put_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.fail_on_put = fail_on_put

    def put_object(self, **kwargs):
        if self.fail_on_put:
            raise RuntimeError("simulated S3 outage for bucket secret-bucket")
        self.put_calls.append(kwargs)

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)


def test_r2_storage_request_shape_and_urls():
    client = _FakeS3Client()
    storage = R2Storage(client, bucket="staging-bucket", public_base_url="https://cdn.example.com/")

    url = storage.save("42_20261101_abc123_photo.png", PNG, "image/png")
    assert url == "https://cdn.example.com/products/42_20261101_abc123_photo.png"
    assert len(client.put_calls) == 1
    call = client.put_calls[0]
    assert call["Bucket"] == "staging-bucket"
    assert call["Key"] == "products/42_20261101_abc123_photo.png"
    assert call["ContentType"] == "image/png"
    assert call["Body"] == PNG

    assert storage.delete_url(url) is True
    assert client.delete_calls == [
        {"Bucket": "staging-bucket", "Key": "products/42_20261101_abc123_photo.png"}
    ]


def test_r2_storage_failure_is_generic_and_never_leaks_context():
    client = _FakeS3Client(fail_on_put=True)
    storage = R2Storage(client, bucket="secret-bucket", public_base_url="https://cdn.example.com")

    with pytest.raises(StorageError) as excinfo:
        storage.save("photo.png", PNG, "image/png")

    message = str(excinfo.value)
    assert message == "image storage is unavailable"
    assert "secret-bucket" not in message
    assert "simulated" not in message
    assert not client.put_calls


def test_r2_delete_is_best_effort_on_failure():
    class _Boom(_FakeS3Client):
        def delete_object(self, **kwargs):
            raise RuntimeError("nope")

    storage = R2Storage(_Boom(), bucket="b", public_base_url="https://cdn.example.com")
    assert storage.delete_url("https://cdn.example.com/products/x.png") is False
    assert storage.delete_url("not a url") is False


def test_backend_selection_and_fail_closed_configuration(monkeypatch):
    # Default: local disk.
    assert get_storage().name == "local"

    # r2 selected without credentials -> validation refuses to load settings.
    with pytest.raises(ValidationError):
        Settings(storage_backend="r2")

    with pytest.raises(ValidationError):
        Settings(storage_backend="ftp")

    full = Settings(
        storage_backend="r2",
        aws_access_key_id="k",
        aws_secret_access_key="s",
        aws_s3_bucket="b",
        aws_s3_endpoint="https://account.r2.cloudflarestorage.com",
        storage_public_base_url="https://cdn.example.com",
    )
    assert full.storage_backend == "r2"

    # With complete configuration the getter constructs the R2 backend.
    monkeypatch.setattr(settings, "storage_backend", "r2")
    monkeypatch.setattr(settings, "aws_access_key_id", "k")
    monkeypatch.setattr(settings, "aws_secret_access_key", "s")
    monkeypatch.setattr(settings, "aws_s3_bucket", "b")
    monkeypatch.setattr(settings, "aws_s3_endpoint", "https://account.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "storage_public_base_url", "https://cdn.example.com")
    reset_storage_cache()
    assert get_storage().name == "r2"


# ------------------------------------------------------------- HTTP surface


def _api(seller: dict, path: str) -> str:
    return f"/api/v1/businesses/{seller['business_id']}{path}"


def _upload(client, seller, *, files, name: str = "Storage Product"):
    return client.post(
        _api(seller, "/products/upload"),
        data={
            "name": name,
            "sku": f"STO-{uuid.uuid4().hex[:8]}",
            "cost_price": "10.00",
            "selling_price": "20.00",
            "stock_quantity": "1",
        },
        files=files,
        headers=seller["auth"],
    )


def test_storage_failure_returns_502_and_persists_nothing(client, monkeypatch):
    seller = register_seller(client)

    class _FailingStorage:
        name = "failing"

        def save(self, filename, data, content_type):
            raise StorageError("image storage is unavailable")

        def delete_url(self, url):
            return False

    monkeypatch.setattr("app.products.upload_router.get_storage", lambda: _FailingStorage())

    response = _upload(client, seller, files={"file": ("photo.png", PNG, "image/png")})
    assert response.status_code == 502, response.text
    detail = response.json()["detail"]
    assert detail == "Image storage is temporarily unavailable"
    for leak in ("boto", "bucket", "key", "endpoint", "aws"):
        assert leak not in detail.lower()

    # No half-created product, no orphaned image row.
    assert client.get(_api(seller, "/products/"), headers=seller["auth"]).json() == []


def test_oversized_upload_rejected_before_storage(client):
    seller = register_seller(client)
    oversized = b"0" * (settings.max_upload_size + 1)
    response = _upload(client, seller, files={"file": ("big.png", oversized, "image/png")})
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()
    assert client.get(_api(seller, "/products/"), headers=seller["auth"]).json() == []


def test_invalid_content_type_rejected(client):
    seller = register_seller(client)
    response = _upload(client, seller, files={"file": ("payload.exe", b"MZ..", "application/x-msdownload")})
    assert response.status_code == 400
    assert client.get(_api(seller, "/products/"), headers=seller["auth"]).json() == []


def test_upload_then_product_delete_cleans_the_object(client, tmp_path, monkeypatch):
    seller = register_seller(client)
    storage = LocalStorage(str(tmp_path))
    monkeypatch.setattr("app.products.upload_router.get_storage", lambda: storage)
    monkeypatch.setattr("app.products.router.get_storage", lambda: storage)

    created = _upload(client, seller, files={"file": ("photo.png", PNG, "image/png")})
    assert created.status_code == 201, created.text
    body = created.json()
    stored_name = body["image_url"].rsplit("/", 1)[-1]
    assert (tmp_path / stored_name).exists()

    # Retrieval through the app (local backend serves /uploads from the real
    # directory; here we assert the URL shape + object existence instead).
    assert body["image_url"].startswith("/uploads/")

    deleted = client.delete(_api(seller, f"/products/{body['id']}"), headers=seller["auth"])
    assert deleted.status_code == 204
    assert not (tmp_path / stored_name).exists(), "stored object was not cleaned up"


def test_upload_is_tenant_scoped(client, tmp_path, monkeypatch):
    seller_a = register_seller(client)
    seller_b = register_seller(client)
    storage = LocalStorage(str(tmp_path))
    monkeypatch.setattr("app.products.upload_router.get_storage", lambda: storage)

    response = _upload(client, seller_b, files={"file": ("photo.png", PNG, "image/png")})
    # B uploading to B's own path is fine; A's path must be denied for B.
    assert response.status_code == 201
    denied = client.post(
        _api(seller_a, "/products/upload"),
        data={
            "name": "x",
            "sku": "X-1",
            "cost_price": "1.00",
            "selling_price": "1.00",
            "stock_quantity": "0",
        },
        files={"file": ("photo.png", PNG, "image/png")},
        headers=seller_b["auth"],
    )
    assert denied.status_code == 403
