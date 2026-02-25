import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connection_select_1():
    # Import inside test so conftest env defaults are applied first.
    from database.engine import async_session

    async with async_session() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
