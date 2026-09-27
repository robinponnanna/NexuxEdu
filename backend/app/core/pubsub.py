import asyncio
from typing import Dict, Any, Set, Optional
import json

class InMemoryBroker:
    """
    High-performance in-memory Pub/Sub and Telemetry Cache broker
    compatible with the Redis semantics specified in SYSTEM_DESIGN.md.
    Provides sub-millisecond dispatch to WebSocket subscribers.
    """
    def __init__(self):
        self._channels: Dict[str, Set[asyncio.Queue]] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        async with self._lock:
            subscribers = self._channels.get(channel, set())
            payload = json.dumps(message)
            delivered = 0
            for queue in list(subscribers):
                try:
                    queue.put_nowait(payload)
                    delivered += 1
                except asyncio.QueueFull:
                    pass
            return delivered

    async def subscribe(self, channel: str) -> asyncio.Queue:
        async with self._lock:
            if channel not in self._channels:
                self._channels[channel] = set()
            queue = asyncio.Queue(maxsize=100)
            self._channels[channel].add(queue)
            return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            if channel in self._channels:
                self._channels[channel].discard(queue)
                if not self._channels[channel]:
                    del self._channels[channel]

    async def hset(self, key: str, mapping: Dict[str, Any]) -> None:
        async with self._lock:
            if key not in self._cache:
                self._cache[key] = {}
            self._cache[key].update(mapping)

    async def hgetall(self, key: str) -> Dict[str, Any]:
        async with self._lock:
            return dict(self._cache.get(key, {}))

    async def set_bus_telemetry(self, bus_id: int, telemetry: Dict[str, Any]) -> None:
        await self.hset(f"bus:telemetry:{bus_id}", telemetry)
        await self.publish(f"channel:bus:{bus_id}", telemetry)

    async def get_bus_telemetry(self, bus_id: int) -> Optional[Dict[str, Any]]:
        data = await self.hgetall(f"bus:telemetry:{bus_id}")
        return data if data else None

broker = InMemoryBroker()
