"""WS /ws/news/{symbol} : pousse en direct les nouvelles news de la paire (Redis Pub/Sub -> navigateur).

Messages envoyés : {"type": "status", "live": bool}, {"type": "news", "data": {...}}, {"type": "ping"}.
"""

import asyncio
import json

import redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.api.pairs import find_pair
from app.core.logging import get_logger
from app.database import SessionLocal
from app.redis_client import NEWS_CHANNEL, ensure_available, get_async_redis
from app.services import pair_mapping

router = APIRouter(tags=["websocket"])
logger = get_logger(__name__)

PING_INTERVAL_SECONDS = 25
CLOSE_UNKNOWN_PAIR = 4404
CLOSE_UNAVAILABLE = 1011


def _pair_tags(symbol: str) -> set[str] | None:
    with SessionLocal() as db:
        pair = find_pair(db, symbol)
        if pair is None:
            return None
        return set(pair_mapping.news_tags(pair.base_currency, pair.quote_currency, pair.category))


@router.websocket("/ws/news/{symbol}")
async def news_socket(websocket: WebSocket, symbol: str) -> None:
    tags = await run_in_threadpool(_pair_tags, symbol)
    await websocket.accept()
    if tags is None:
        await websocket.close(code=CLOSE_UNKNOWN_PAIR, reason="Marché inconnu")
        return

    try:
        ensure_available()
        pubsub = get_async_redis().pubsub()
        await pubsub.subscribe(NEWS_CHANNEL)
    except (redis.RedisError, OSError) as exc:
        logger.warning("WebSocket news : Redis indisponible (%s)", exc)
        await websocket.send_json({"type": "status", "live": False})
        await websocket.close(code=CLOSE_UNAVAILABLE, reason="Temps réel indisponible")
        return

    send_lock = asyncio.Lock()

    async def send(message: dict) -> None:
        async with send_lock:
            await websocket.send_json(message)

    await send({"type": "status", "live": True})

    async def forward() -> None:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (TypeError, ValueError):
                continue
            if tags & set(payload.get("currencies", [])):
                await send({"type": "news", "data": payload})

    async def keepalive() -> None:
        # Évite que les proxys (Nginx, hébergeurs) coupent une connexion silencieuse.
        while True:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            await send({"type": "ping"})

    async def listen() -> None:
        # Le client n'envoie rien d'utile : cette boucle sert à détecter la déconnexion.
        while True:
            await websocket.receive_text()

    tasks = [asyncio.create_task(forward()), asyncio.create_task(keepalive()), asyncio.create_task(listen())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                logger.warning("WebSocket news %s fermé : %s", symbol, exc)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await pubsub.unsubscribe(NEWS_CHANNEL)
            await pubsub.aclose()
        except (redis.RedisError, OSError):
            pass
