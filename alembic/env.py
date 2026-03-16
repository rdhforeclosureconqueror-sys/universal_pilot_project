import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ---------------------------------------------------
# Load environment variables
# ---------------------------------------------------
load_dotenv()

# ---------------------------------------------------
# Ensure project root is on the Python path
# ---------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ---------------------------------------------------
# Import SQLAlchemy Base
# ---------------------------------------------------
from app.models.base import Base

# ---------------------------------------------------
# Import ALL models so Alembic can detect them
# This registers them with Base.metadata
# ---------------------------------------------------
import app.models.users
import app.models.properties
import app.models.lead_intelligence
import app.models.cases
import app.models.housing_intelligence
import app.models.essential_worker
import app.models.ai_command_logs

# ---------------------------------------------------
# Alembic configuration object
# ---------------------------------------------------
config = context.config

# ---------------------------------------------------
# Set database URL from environment
# ---------------------------------------------------
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/universal_case_os"
)

config.set_main_option("sqlalchemy.url", database_url)

# ---------------------------------------------------
# Logging configuration
# ---------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------
# Metadata used for autogeneration
# ---------------------------------------------------
target_metadata = Base.metadata


# ---------------------------------------------------
# Offline migrations
# ---------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------
# Online migrations
# ---------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in online mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------
# Run migration mode
# ---------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
