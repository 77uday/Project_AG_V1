# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime
from types import SimpleNamespace

from core.session.session_boundary_detector import SessionBoundaryDetector
from core.events.session_events import SessionStartEvent, SessionEndEvent


# ============================================================
# TEST HELPERS
# ============================================================

def candle_event(timestamp, o, h, l, c):
    """
    Build a minimal CandleClosedEvent-like object for testing.
    Uses explicit timestamps to guarantee determinism.
    """
    return SimpleNamespace(
        timestamp=timestamp,
        open=o,
        high=h,
        low=l,
        close=c,
    )


# ============================================================
# TESTS — SESSION BOUNDARY DETECTION
# ============================================================

def test_single_day_session_emits_start_only(event_bus, logger):
    """
    Single trading day:
    - One SessionStartEvent
    - No SessionEndEvent
    """

    captured_events = []

    event_bus.subscribe(SessionStartEvent, lambda e: captured_events.append(e))
    event_bus.subscribe(SessionEndEvent, lambda e: captured_events.append(e))

    detector = SessionBoundaryDetector(event_bus, logger)

    detector.on_candle_closed(
        candle_event(datetime(2026, 1, 10, 9, 15), 100, 105, 99, 104)
    )

    detector.on_candle_closed(
        candle_event(datetime(2026, 1, 10, 9, 16), 104, 106, 103, 105)
    )

    starts = [e for e in captured_events if isinstance(e, SessionStartEvent)]
    ends = [e for e in captured_events if isinstance(e, SessionEndEvent)]

    assert len(starts) == 1
    assert len(ends) == 0


def test_two_day_boundary_emits_end_and_next_start(event_bus, logger):
    """
    Two trading days:
    - Day 1 → SessionStart + SessionEnd
    - Day 2 → SessionStart
    - Previous day OHLC correctly transferred
    """

    captured_events = []

    event_bus.subscribe(SessionStartEvent, lambda e: captured_events.append(e))
    event_bus.subscribe(SessionEndEvent, lambda e: captured_events.append(e))

    detector = SessionBoundaryDetector(event_bus, logger)

    # Day 1 candles
    detector.on_candle_closed(
        candle_event(datetime(2026, 1, 10, 9, 15), 100, 110, 95, 105)
    )
    detector.on_candle_closed(
        candle_event(datetime(2026, 1, 10, 15, 29), 105, 112, 104, 110)
    )

    # Day 2 first candle
    detector.on_candle_closed(
        candle_event(datetime(2026, 1, 11, 9, 15), 120, 121, 119, 120)
    )

    starts = [e for e in captured_events if isinstance(e, SessionStartEvent)]
    ends = [e for e in captured_events if isinstance(e, SessionEndEvent)]

    assert len(starts) == 2
    assert len(ends) == 1

    day2_context = starts[1].session_context

    assert day2_context.prev_day_open == 100
    assert day2_context.prev_day_high == 112
    assert day2_context.prev_day_low == 95
    assert day2_context.prev_day_close == 110


def test_session_boundary_detector_is_deterministic(event_bus_factory, logger_factory):
    """
    Same candle stream → same emitted events (order + timestamps).
    """

    def run_once():
        event_bus = event_bus_factory()
        logger = logger_factory()

        emitted = []

        event_bus.subscribe(
            SessionStartEvent,
            lambda e: emitted.append(("START", e.timestamp)),
        )
        event_bus.subscribe(
            SessionEndEvent,
            lambda e: emitted.append(("END", e.timestamp)),
        )

        detector = SessionBoundaryDetector(event_bus, logger)

        candles = [
            candle_event(datetime(2026, 1, 10, 9, 15), 100, 105, 99, 104),
            candle_event(datetime(2026, 1, 10, 15, 29), 104, 106, 103, 105),
            candle_event(datetime(2026, 1, 11, 9, 15), 110, 111, 109, 110),
        ]

        for c in candles:
            detector.on_candle_closed(c)

        return emitted

    assert run_once() == run_once()
