"""Alembic environment configuration for DVP FastAPI.

Uses a **synchronous** SQLAlchemy engine — Alembic is a CLI tool and does
not benefit from async; using async engines inside Alembic's migration
context causes greenlet/event-loop incompatibilities with psycopg3.

The application itself continues to use the async engine (create_async_engine)
via app/core/database/postgres.py; only the migration runner is synchronous.
"""

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ---------------------------------------------------------------------------
# Pull the database URL from application settings at runtime.
#
# The app uses `postgresql+psycopg://…` (psycopg3 async driver).
# For Alembic we switch to `postgresql+psycopg2://…` if psycopg2 is present,
# OR keep `postgresql+psycopg://…` which works fine in synchronous mode too
# (psycopg3 supports both sync and async).  We just must NOT wrap it in an
# async_engine_from_config call.
# ---------------------------------------------------------------------------
from app.core.config.settings import settings  # noqa: E402

# Override the blank sqlalchemy.url from alembic.ini with the real URL.
config.set_main_option("sqlalchemy.url", settings.get_database_url.replace("%", "%%"))

# ---------------------------------------------------------------------------
# Import ALL models so Base.metadata is fully populated for autogenerate.
# ---------------------------------------------------------------------------
from app.models import (  # noqa: F401, E402
    Base,
    User,
    Role,
    Company,
    Department,
    Employee,
    Subscription,
    SubscriptionPlan,
    SubscriptionRequest,
    SubscriptionUsage,
    EmailLog,
    Document,
    Notification,
    AuditLog,
    OTPRecord,
    PasswordResetToken,
)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — emit SQL script without a live DB connection
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — run against a live synchronous DB connection
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
