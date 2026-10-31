from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Normalise PostgreSQL URLs to the project's canonical psycopg (v3) driver.

    Managed providers (e.g. the Vercel/Neon marketplace integration) hand out
    plain ``postgresql://`` or legacy ``postgres://`` URLs. SQLAlchemy resolves
    those to psycopg2, which this project does not install, and the app would
    fail while creating the engine. Accept all three schemes; leave the
    canonical ``postgresql+psycopg://`` form untouched.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


# Create the SQLAlchemy engine.
# `prepare_threshold=None` disables psycopg's automatic server-side prepared
# statements, which are incompatible with transaction-mode connection poolers
# (Neon/pgbouncer) used by managed staging deployments. The cost on direct
# connections is negligible for this workload.
engine = create_engine(
    normalize_database_url(settings.database_url),
    echo=settings.app_debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,       # Verify connections are alive before using them
    connect_args={"prepare_threshold": None},
)


# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    pass
