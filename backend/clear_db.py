"""Script to clear all data from the database."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings


async def clear_database():
    """Clear all data from all tables."""
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        # Disable foreign key checks and truncate all tables
        await conn.execute(text("""
            TRUNCATE TABLE
                analysis_results,
                query_executions,
                questions,
                brands,
                users,
                brand_research
            CASCADE
        """))
        print("All tables cleared successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_database())
