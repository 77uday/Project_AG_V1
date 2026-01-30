# ============================================================
# IMPORTS
# ============================================================

from collections import defaultdict
from typing import Callable, Dict, List


# ============================================================
# EVENT BUS
# ============================================================

class EventBus:
    def __init__(self):
        # event_type -> list of handlers
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        print("[OK] EventBus initialized")

    # ========================================================
    # SUBSCRIPTION API
    # ========================================================

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for a given event type.
        """
        self._subscribers[event_type].append(handler)
    
    # ========================================================
    # PUBLISH API
    # ========================================================

    def publish(self, event_type: str, payload) -> None:
        """
        Publish an event to all subscribed handlers.
        """
        handlers = self._subscribers.get(event_type, [])

        for handler in handlers:
            handler(payload)
