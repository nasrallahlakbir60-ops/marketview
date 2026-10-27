import asyncio

import httpx

from app.main import app


def test_health_returns_ok() -> None:
    async def get_health() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.get("/health")

    response = asyncio.run(get_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_error_returns_clean_503(client, database) -> None:
    from app.database import Base, engine

    Base.metadata.drop_all(engine)  # simule une base sans tables / injoignable

    response = client.get("/api/pairs")

    assert response.status_code == 503
    assert "indisponible" in response.json()["detail"]
