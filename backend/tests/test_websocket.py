import json
import threading
import time

import pytest
from starlette.websockets import WebSocketDisconnect

from app.redis_client import NEWS_CHANNEL


def _publish_soon(fake_redis, payloads: list[dict], delay: float = 0.2) -> None:
    def publish() -> None:
        time.sleep(delay)
        for payload in payloads:
            fake_redis.publish(NEWS_CHANNEL, json.dumps(payload))

    threading.Thread(target=publish, daemon=True).start()


def test_websocket_forwards_only_matching_news(client, seeded, fake_redis) -> None:
    with client.websocket_connect("/ws/news/EURUSD") as ws:
        assert ws.receive_json() == {"type": "status", "live": True}
        _publish_soon(fake_redis, [
            {"id": 1, "title": "BoJ news", "currencies": ["JPY"]},
            {"id": 2, "title": "ECB news", "currencies": ["EUR"]},
        ])

        message = ws.receive_json()
        # Laisse l'application se désabonner avant que le TestClient n'annule sa tâche.
        ws.close()
        time.sleep(0.2)

    assert message == {"type": "news", "data": {"id": 2, "title": "ECB news", "currencies": ["EUR"]}}


def test_websocket_unknown_pair_is_closed(client, seeded) -> None:
    with client.websocket_connect("/ws/news/NOPE") as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 4404


def test_scheduler_registers_news_job() -> None:
    from app.workers.scheduler import create_scheduler

    scheduler = create_scheduler()
    job = scheduler.get_job("fetch_news")

    assert job is not None
    assert job.trigger.interval.total_seconds() == 60
