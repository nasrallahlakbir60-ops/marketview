import asyncio

from app.services import serverless


def _reset(monkeypatch) -> list[str]:
    calls: list[str] = []

    async def fake_news():
        calls.append("news")
        return 1

    monkeypatch.setattr(serverless, "JOBS", {**serverless.JOBS, "news": fake_news})
    monkeypatch.setattr(serverless, "_last_refresh", {})
    monkeypatch.setattr(serverless, "_running", set())
    return calls


def test_refresh_does_nothing_outside_vercel(monkeypatch) -> None:
    monkeypatch.delenv("VERCEL", raising=False)
    calls = _reset(monkeypatch)

    asyncio.run(serverless.refresh_if_stale("news")())

    assert calls == []


def test_refresh_runs_once_per_interval_on_vercel(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    calls = _reset(monkeypatch)
    refresh = serverless.refresh_if_stale("news")

    asyncio.run(refresh())
    asyncio.run(refresh())

    assert calls == ["news"]


def test_refresh_failure_is_swallowed(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    _reset(monkeypatch)

    async def failing():
        raise RuntimeError("boom")

    monkeypatch.setattr(serverless, "JOBS", {"news": failing})

    asyncio.run(serverless.refresh_if_stale("news")())

    assert serverless._running == set()


def test_ensure_database_initializes_once_on_vercel(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(serverless, "_database_ready", False)
    calls: list[int] = []
    monkeypatch.setattr(serverless, "initialize_database", lambda: calls.append(1))

    asyncio.run(serverless.ensure_database())
    asyncio.run(serverless.ensure_database())

    assert calls == [1]
