"""Create (or verify) the isolated local test database.

Usage (from the backend directory):

    .venv\\Scripts\\python.exe scripts/create_test_db.py

Reads DATABASE_URL from the environment / .env, derives
`sellflow_migration_test` on the same host and user, and creates it when it
does not exist. The database name always ends in `_test` and is never the
configured application database, so no existing data is touched.

This exists because the migration requires tests to run against an isolated
database (see tests/conftest.py, which refuses to run otherwise).
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv

TEST_DB_NAME = "sellflow_migration_test"


def _redact(url: str) -> str:
    parts = urlsplit(url)
    netloc = parts.netloc
    if "@" in netloc:
        userinfo, host = netloc.rsplit("@", 1)
        user = userinfo.split(":", 1)[0]
        netloc = f"{user}:***@{host}"
    return urlunsplit(parts._replace(netloc=netloc))


def _with_database(url: str, database: str) -> str:
    """Return `url` with the database (path) replaced."""
    return urlunsplit(urlsplit(url)._replace(path=f"/{database}"))


def main() -> int:
    load_dotenv()
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is not set (environment or .env).", file=sys.stderr)
        return 1
    if not url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        print("Only PostgreSQL URLs are supported.", file=sys.stderr)
        return 1

    psycopg_url = url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )
    admin_url = _with_database(psycopg_url, "postgres")
    test_url = _with_database(psycopg_url, TEST_DB_NAME)

    try:
        with psycopg.connect(admin_url, autocommit=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,)
            ).fetchone()
            if exists:
                print(f"Test database already exists: {_redact(test_url)}")
            else:
                connection.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
                print(f"Created test database: {_redact(test_url)}")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not create the test database: {type(exc).__name__}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
