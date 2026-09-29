from typing import List, Tuple, Dict, Any, Optional
from app.core.pubsub import broker

class NotificationCollector:
    """
    Collects notifications and real-time messages during a database transaction.
    Pushes to InMemoryBroker strictly AFTER a successful commit.
    If the transaction rolls back or fails, flush() is never called,
    ensuring a rolled-back transition never produces a live notification.
    """
    def __init__(self):
        self._pending: List[Tuple[str, Dict[str, Any]]] = []

    def queue_publish(self, channel: str, message: Dict[str, Any]) -> None:
        self._pending.append((channel, message))

    async def flush(self) -> int:
        count = 0
        for channel, msg in self._pending:
            await broker.publish(channel, msg)
            count += 1
        self._pending.clear()
        return count

    def clear(self) -> None:
        self._pending.clear()
