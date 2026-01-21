"""
Database configuration and session management.
Supports both PostgreSQL and SQLite for development.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from .config import settings


# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    metadata = metadata


# Create async engine with appropriate settings for database type
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": settings.DATABASE_ECHO,
}

if not is_sqlite:
    # PostgreSQL-specific settings
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and run migrations."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)

        # Run migrations to add OAuth columns if they don't exist
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR(500)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255)",
        ]

        for migration in migrations:
            try:
                await conn.execute(text(migration))
            except Exception:
                # Column might already exist
                pass


async def close_db():
    """Close database connections."""
    await engine.dispose()
