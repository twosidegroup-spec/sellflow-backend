"""Unit coverage for the database-URL normalisation used by managed providers.

Vercel/Neon marketplace integrations inject plain `postgresql://` (or legacy
`postgres://`) URLs; SQLAlchemy would resolve those to psycopg2, which this
project does not install. `normalize_database_url` maps every supported scheme
to the canonical psycopg (v3) driver and leaves anything else untouched.
"""

from __future__ import annotations

from app.db.engine import normalize_database_url


def test_plain_and_legacy_schemes_are_mapped_to_psycopg():
    assert (
        normalize_database_url("postgresql://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert (
        normalize_database_url("postgres://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_canonical_and_unrelated_schemes_are_untouched():
    canonical = "postgresql+psycopg://user:pass@host:5432/db?sslmode=require"
    assert normalize_database_url(canonical) == canonical
    assert normalize_database_url("sqlite:///local.db") == "sqlite:///local.db"


def test_query_parameters_and_pooler_hosts_survive_normalisation():
    pooled = "postgresql://user:pass@ep-xyz-pooler.eu-central-1.aws.neon.tech/db?sslmode=require"
    normalised = normalize_database_url(pooled)
    assert normalised.startswith("postgresql+psycopg://")
    assert "-pooler" in normalised and "sslmode=require" in normalised
