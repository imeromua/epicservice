import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_schema_has_required_tables():
    # Import inside test so conftest env defaults are applied first.
    from database.engine import async_session

    required = [
        "products",
        "temp_lists",
    ]

    async with async_session() as session:
        for table in required:
            # to_regclass returns NULL if relation doesn't exist
            res = await session.execute(
                text("SELECT to_regclass(:fqname)")
                .bindparams(fqname=f"public.{table}")
            )
            assert res.scalar_one() is not None, f"Missing table: {table}"
