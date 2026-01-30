# ============================================================
# IMPORTS
# ============================================================

import pytest
from typing import Callable, Dict, List, Any

# ============================================================
# TEST EVENT BUS & LOGGER (TEST HELPERS)
# ============================================================

class TestEventBus:
    """
    Minimal in-memory EventBus used for unit tests.
    - subscribe(key, handler): key can be an event class or a string name
    - publish(event): event is an event instance; dispatches to matching subscribers
    """
    def __init__(self):
        self._subs: Dict[Any, List[Callable]] = {}

    def subscribe(self, key, handler: Callable):
        self._subs.setdefault(key, []).append(handler)

    def publish(self, event):
        """
        Dispatch event to handlers subscribed by:
        - the event class (exact type)
        - the event class's __name__ (string)
        - any subscribers who passed the event class's base classes (isinstance)
        """
        # If a string was published (rare), dispatch to string-keyed handlers
        if isinstance(event, str):
            for h in self._subs.get(event, []):
                h(None)
            return

        ev_cls = event.__class__
        ev_name = ev_cls.__name__

        # dispatch to handlers subscribed by exact class or by class name
        for key, handlers in list(self._subs.items()):
            try:
                if key is ev_cls or key == ev_name or (isinstance(key, type) and issubclass(ev_cls, key)):
                    for h in handlers:
                        h(event)
            except Exception:
                # defensive: if key is not a type or comparable, ignore
                continue


class TestLogger:
    """
    Simple test logger capturing messages for assertions / debug.
    Methods: info(msg, **kwargs), debug(msg), error(msg)
    """
    def __init__(self):
        self.records = []

    def info(self, msg, **kwargs):
        self.records.append(("INFO", msg, kwargs))

    def debug(self, msg, **kwargs):
        self.records.append(("DEBUG", msg, kwargs))

    def error(self, msg, **kwargs):
        self.records.append(("ERROR", msg, kwargs))


# ============================================================
# PYTEST FIXTURES
# ============================================================

@pytest.fixture
def event_bus():
    """
    Reusable EventBus instance for a test function.
    """
    return TestEventBus()

@pytest.fixture
def logger():
    """
    Reusable TestLogger instance for a test function.
    """
    return TestLogger()

@pytest.fixture
def event_bus_factory():
    """
    Factory that returns a fresh EventBus (for deterministic isolation tests).
    """
    return lambda: TestEventBus()

@pytest.fixture
def logger_factory():
    """
    Factory that returns a fresh TestLogger.
    """
    return lambda: TestLogger()
