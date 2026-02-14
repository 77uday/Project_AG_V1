# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Tuple

import pytest

from strategy.strategy_manager import create_strategy
from strategy.intent_events import IntentEvent, TriggerSpec, Side
from core.derived_data.models import GapSnapshotEvent
from core.derived_data.derived_data_store import InMemoryDerivedDataStore
from core.events.session_events import SessionEndEvent


# ============================================================
# SMALL TEST HELPERS (non-collectable names)
# ============================================================

class _CaptureEventBus:
    """
    Minimal event bus used in tests.
    - subscribe(key, handler)
    - publish(event) => dispatch to handlers where isinstance(event, key)
    Also records a chronological list of published events (for assertions).
    """

    def __init__(self):
        self._subs: Dict[Any, List[Callable]] = {}
        self.published: List[Any] = []

    def subscribe(self, key, handler: Callable):
        self._subs.setdefault(key, []).append(handler)

    def publish(self, event: Any):
        # record for inspection
        self.published.append(event)
        # dispatch to matching subscribers
        for key, handlers in list(self._subs.items()):
            try:
                # key is expected to be a class/type
                if isinstance(event, key):
                    for h in handlers:
                        h(event)
            except Exception:
                # fallback: if key is exactly the event's class object
                if key == type(event):
                    for h in handlers:
                        h(event)


class _TestLogger:
    def __init__(self):
        self.records: List[Tuple[Tuple, Dict]] = []

    def info(self, *args, **kwargs):
        self.records.append((args, kwargs))


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def bus():
    return _CaptureEventBus()


@pytest.fixture
def logger():
    return _TestLogger()


@pytest.fixture
def store():
    return InMemoryDerivedDataStore()


@pytest.fixture
def strategy(bus, logger, store):
    """
    Create the strategy instance (using wrapper create_strategy).
    Strategy subscribes to the bus during creation.
    """
    s = create_strategy(event_bus=bus, logger=logger, store=store, strategy_id="DUMMY-TEST")
    return s


# ============================================================
# HELP: find last published IntentEvent from capture bus
# ============================================================

def _find_last_intent(bus: _CaptureEventBus) -> IntentEvent:
    for ev in reversed(bus.published):
        if isinstance(ev, IntentEvent):
            return ev
    return None


# ============================================================
# TESTS
# ============================================================

def test_strategy_emits_intent_on_gap_snapshot(strategy, bus, store):
    """
    Strategy should pick the symbol with the smallest absolute gap (gap_pct_abs)
    and publish an IntentEvent with step_index == 1 (initial).
    """
    # Prepare gap snapshot with two symbols: AAA (0.2) smaller than BBB (1.0)
    now = datetime.now(timezone.utc)
    gaps = {
        "AAA": {"prev_close": 100.0, "today_open": 100.5, "gap_pct": 0.5, "gap_pct_abs": 0.5},
        "BBB": {"prev_close": 50.0, "today_open": 50.75, "gap_pct": 1.5, "gap_pct_abs": 1.5},
    }

    gap_event = GapSnapshotEvent(timestamp=now, gaps=gaps)

    # Publish gap snapshot
    bus.publish(gap_event)

    # Find last intent published
    intent = _find_last_intent(bus)
    assert intent is not None, "No IntentEvent was published on GapSnapshotEvent"
    assert intent.symbol == "AAA", "Strategy should pick symbol with smallest gap_pct_abs"
    # Both triggers present and step_index should be 1 (first meaningful target)
    assert len(intent.triggers) == 2
    assert intent.triggers[0].step_index == 1
    assert intent.triggers[1].step_index == 1
    assert {t.side for t in intent.triggers} == {Side.LONG, Side.SHORT}


def test_strategy_auto_advance_on_order_fill(strategy, bus, store):
    """
    After initial intent is published, simulate an OrderFillEvent with matching intent id.
    Strategy should auto-advance and publish a new IntentEvent with step_index + 1.
    """

    now = datetime.now(timezone.utc)
    gaps = {
        "X1": {"prev_close": 10.0, "today_open": 10.2, "gap_pct": 2.0, "gap_pct_abs": 2.0},
        "X2": {"prev_close": 20.0, "today_open": 20.5, "gap_pct": 2.5, "gap_pct_abs": 2.5},
    }
    gap_event = GapSnapshotEvent(timestamp=now, gaps=gaps)

    # Publish gap snapshot -> initial intent for X1
    bus.publish(gap_event)
    first_intent = _find_last_intent(bus)
    assert first_intent is not None
    first_id = first_intent.intent_id
    assert first_intent.triggers[0].step_index == 1

    # Create a dummy "OrderFillEvent" shaped object that carries intent_id
    class DummyFill:
        def __init__(self, intent_id):
            self.intent_id = intent_id
            # other fields that OrderFillEvent might have are ignored by DummyStrategy

    fill = DummyFill(first_id)

    # publish the fill -> strategy should handle and emit next intent
    bus.publish(fill)

    # find the next IntentEvent (should be after the fill in the published list)
    # search for an IntentEvent whose id != first_id
    found_next = None
    for ev in reversed(bus.published):
        if isinstance(ev, IntentEvent) and ev.intent_id != first_id:
            found_next = ev
            break

    assert found_next is not None, "Strategy did not publish the next Intent after OrderFill"
    # Step index should have advanced to 2
    assert found_next.triggers[0].step_index == 2


def test_strategy_deactivates_on_session_end(strategy, bus, store):
    """
    After SessionEndEvent, strategy should deactivate and ignore subsequent gap snapshots.
    """
    now = datetime.now(timezone.utc)
    gaps1 = {
        "A": {"prev_close": 100.0, "today_open": 100.0, "gap_pct": 0.0, "gap_pct_abs": 0.0},
    }
    gap_event1 = GapSnapshotEvent(timestamp=now, gaps=gaps1)

    # Publish first gap -> initial intent
    bus.publish(gap_event1)
    first_intent = _find_last_intent(bus)
    assert first_intent is not None

    # Publish session end
    session_end = SessionEndEvent(timestamp=now, session_context=None)
    bus.publish(session_end)

    # Clear previously published intents for clarity
    bus.published.clear()

    # Publish another gap snapshot after session end
    gaps2 = {
        "B": {"prev_close": 50.0, "today_open": 50.0, "gap_pct": 0.0, "gap_pct_abs": 0.0},
    }
    gap_event2 = GapSnapshotEvent(timestamp=datetime.now(timezone.utc), gaps=gaps2)
    bus.publish(gap_event2)

    # No new IntentEvents should be published after deactivation
    intents_after = [e for e in bus.published if isinstance(e, IntentEvent)]
    assert len(intents_after) == 0, "Strategy published intents after SessionEndEvent (should be deactivated)"
