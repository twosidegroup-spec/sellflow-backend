"""Object storage for product images.

Two backends, selected by ``STORAGE_BACKEND`` (see ``app/core/config.py``):

* ``local`` — the historical behaviour: files under ``backend/uploads/`` served
  by the ``/uploads`` static mount. Fine for development and hosts with a
  persistent disk; **ephemeral on serverless platforms**.
* ``r2`` — Cloudflare R2 through its S3-compatible API (boto3). Durable, and
  the intended backend for deployed staging/pilot environments. R2 has no
  egress fees and a free tier; see ``PILOT_READINESS_REPORT.md``.

Security properties preserved across backends:

* object names are always generated server-side (128 bits of randomness plus a
  sanitized stem — see ``upload_router``); the client's filename is never
  trusted;
* the stored extension is derived from the *validated content type*;
* credentials live only in environment variables — they are never written to
  logs, exceptions, URLs or reports;
* failures raise :class:`StorageError` with a generic message; details are
  logged server-side (boto3 exceptions can echo request context, so they are
  never surfaced to clients).

``delete_url`` is best-effort by design: a failed cleanup must never fail a
seller's request.
"""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("sellflow.storage")

# Canonical upload directory for the local backend (contains .gitkeep).
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
)

# Object-key prefix for the R2 backend, e.g. `products/<filename>`.
R2_KEY_PREFIX = "products"

# A safe stored filename: one path segment, conservative character set.
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


class StorageError(RuntimeError):
    """A storage operation failed. The message is client-safe (no details)."""


class StorageBackend(Protocol):
    name: str

    def save(self, filename: str, data: bytes, content_type: str) -> str:
        """Persist ``data`` and return the public URL to serve it from."""

    def delete_url(self, url: str) -> bool:
        """Best-effort deletion of a previously stored object."""


def _filename_from_url(url: str | None) -> str | None:
    """Extract a safe stored filename from a URL we (or the DB) holds.

    Returns ``None`` for anything that is not a single, conservative path
    segment. Any URL containing traversal markers is refused outright
    (defence in depth — the value still has to pass the filename pattern, and
    it is only ever joined to the configured storage directory/prefix).
    """
    if not url or ".." in url:
        return None
    candidate = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    if _SAFE_FILENAME.match(candidate):
        return candidate
    return None


class LocalStorage:
    """Disk-backed storage under ``uploads/`` (development / persistent hosts)."""

    name = "local"

    def __init__(self, directory: str = UPLOAD_DIR) -> None:
        self.directory = directory
        try:
            os.makedirs(self.directory, exist_ok=True)
        except OSError:
            # Serverless bundles are read-only; the write attempt will raise
            # StorageError with a clear message instead of failing at import.
            logger.warning("local storage directory is not writable at import time")

    def save(self, filename: str, data: bytes, content_type: str) -> str:
        if not _SAFE_FILENAME.match(filename):
            raise StorageError("invalid storage filename")
        try:
            with open(os.path.join(self.directory, filename), "wb") as handle:
                handle.write(data)
        except OSError as exc:
            logger.exception("local storage write failed")
            raise StorageError("image storage is unavailable") from exc
        return f"/uploads/{filename}"

    def delete_url(self, url: str) -> bool:
        filename = _filename_from_url(url)
        if filename is None:
            return False
        try:
            os.remove(os.path.join(self.directory, filename))
            return True
        except FileNotFoundError:
            return False
        except OSError:
            logger.warning("local storage delete failed")
            return False


class R2Storage:
    """Cloudflare R2 (S3-compatible) storage for deployed environments."""

    name = "r2"

    def __init__(self, client, bucket: str, public_base_url: str, prefix: str = R2_KEY_PREFIX) -> None:
        self._client = client
        self._bucket = bucket
        self._base = public_base_url.rstrip("/")
        self._prefix = prefix

    @classmethod
    def from_settings(cls) -> "R2Storage":
        try:
            import boto3  # imported lazily: only required when r2 is selected
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                "STORAGE_BACKEND=r2 requires the boto3 package (pip install boto3)"
            ) from exc

        client = boto3.client(
            "s3",
            endpoint_url=settings.aws_s3_endpoint,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region or "auto",
        )
        return cls(
            client=client,
            bucket=settings.aws_s3_bucket,
            public_base_url=settings.storage_public_base_url,
        )

    def _key_for(self, filename: str) -> str:
        return f"{self._prefix}/{filename}"

    def save(self, filename: str, data: bytes, content_type: str) -> str:
        if not _SAFE_FILENAME.match(filename):
            raise StorageError("invalid storage filename")
        key = self._key_for(filename)
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except Exception as exc:  # boto3 raises a wide family; never leak details
            logger.exception("r2 storage write failed")
            raise StorageError("image storage is unavailable") from exc
        return f"{self._base}/{key}"

    def delete_url(self, url: str) -> bool:
        filename = _filename_from_url(url)
        if filename is None:
            return False
        try:
            self._client.delete_object(Bucket=self._bucket, Key=self._key_for(filename))
            return True
        except Exception:  # noqa: BLE001 - cleanup must never raise into the request
            logger.warning("r2 storage delete failed")
            return False


@lru_cache
def get_storage() -> StorageBackend:
    """The configured storage backend (cached; call ``reset_storage_cache`` in tests)."""
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "r2":
        return R2Storage.from_settings()
    return LocalStorage()


def reset_storage_cache() -> None:
    """Clear the cached backend (used by tests and settings changes)."""
    get_storage.cache_clear()
