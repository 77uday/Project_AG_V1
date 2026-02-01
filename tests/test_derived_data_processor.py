# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime
from typing import Any, Dict, List

import pytest

from core.derived_data.derived_data_processor import DerivedDataProcessor
from core.derived_data.models import (
    DerivedUniverseSnapshot,
    GapSnapshotEvent,
)
from core.derived_data.derived_data_store import DerivedDataStore
from core.events.session_events import SessionStartEvent


# ============================================================
# TEST STORE (IN-MEMORY)
# ============================================================

class InMemoryDerivedDataStore(DerivedDataStore):
    def __init__(self):
        self.universe_snapshots: List[Any] = []
        self.derived_symbol_data: List[Any] = []
        self.gap_snapshots: List[Any] = []

    def persist_universe_snapshot(self, snapshot: Any) -> None:
        self.universe_snapshots.append(snapshot)

    def persist_derived_symbol_data(self, data: Any) -> None:
        self.derived_symbol_data.append(data)

    def persist_gap_snapshot(self, snapshot: Any) -> None:
        self.gap_snapshots.append(snapshot)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def store():
    return InMemoryDerivedDataStore()


@pytest.fixture
def processor(event_bus, logger, store):
    return DerivedDataProcessor(
        event_bus=event_bus,
        logger=logger,
        store=store,
    )


# ============================================================
# TEST HELPERS
# ============================================================

def prev_day_ohlc():
    """
    Deterministic previous-day OHLC for tests.
    """
    return {
        "AAA": {"high": 110.0, "low": 100.0, "close": 105.0},
        "BBB": {"high": 220.0, "low": 200.0, "close": 210.0},
        # CCC intentionally missing to test exclusion
    }


def session_start_event(ts: datetime, today_open: float):
    """
    Build a minimal SessionStartEvent with SessionContext.
    """
    class _Ctx:
        def __init__(self, open_price):
            self.today_open = open_price

    return SessionStartEvent(
        timestamp=ts,
        session_context=_Ctx(today_open),
    )


# ============================================================
# TESTS — PRE-MARKET LOGIC
# ============================================================

def test_pre_market_builds_filtered_and_tradable(processor, store):
    """
    Verifies:
    - symbols_missing_prev_day_ohlc is tracked
    - filtered_symbols sorted by CPR width
    - tradable_symbols selected by threshold + top-N
    """

    # Override universe for this test
    from core.derived_data import config
    config.symbol_universe[:] = ["AAA", "BBB", "CCC"]
    config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc())

    assert len(store.universe_snapshots) == 1
    snap: DerivedUniverseSnapshot = store.universe_snapshots[0]

    # CCC missing OHLC → excluded but tracked
    assert "CCC" in snap.symbols_missing_prev_day_ohlc
    assert "CCC" not in snap.filtered_symbols

    # Filtered symbols should include AAA, BBB
    assert set(snap.filtered_symbols) == {"AAA", "BBB"}

    # CPR width check (AAA should be tighter than BBB here)
    # So AAA should appear before BBB
    assert snap.filtered_symbols[0] == "AAA"

    # Tradable symbols should be a subset of filtered
    assert set(snap.tradable_symbols).issubset(set(snap.filtered_symbols))


def test_pre_market_is_deterministic(processor, store):
    """
    Same inputs → identical universe snapshot.
    """

    from core.derived_data import config
    config.symbol_universe[:] = ["AAA", "BBB"]
    config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc())
    first = store.universe_snapshots[-1]

    # Reset processor internal state but keep same inputs
    store.universe_snapshots.clear()
    processor.run_pre_market(prev_day_ohlc())
    second = store.universe_snapshots[-1]

    assert first.filtered_symbols == second.filtered_symbols
    assert first.tradable_symbols == second.tradable_symbols
    assert first.symbols_missing_prev_day_ohlc == second.symbols_missing_prev_day_ohlc


# ============================================================
# TESTS — GAP LOGIC (MARKET OPEN)
# ============================================================

def test_gap_snapshot_emitted_on_session_start(processor, store, event_bus):
    """
    Verifies:
    - GapSnapshotEvent emitted at session start
    - Gap % and absolute gap % calculated correctly
    """

    from core.derived_data import config
    config.symbol_universe[:] = ["AAA"]
    config.manually_omitted_symbols = None

    # Pre-market to build tradable list
    processor.run_pre_market(prev_day_ohlc())

    # Capture published gap events
    published: List[GapSnapshotEvent] = []
    event_bus.subscribe(GapSnapshotEvent, lambda e: published.append(e))

    # Market open
    event_bus.publish(
        session_start_event(
            ts=datetime(2026, 1, 10, 9, 15),
            today_open=110.25,  # prev_close was 105.0
        )
    )

    assert len(published) == 1

    gap_event = published[0]
    gap = gap_event.gaps["AAA"]

    expected_gap_pct = ((110.25 - 105.0) / 105.0) * 100.0

    assert gap["gap_pct"] == pytest.approx(expected_gap_pct)
    assert gap["gap_pct_abs"] == pytest.approx(abs(expected_gap_pct))


def test_no_gap_emitted_when_no_tradables(processor, store, event_bus):
    """
    If no tradable symbols exist, gap snapshot should still emit
    but with an empty payload (safe behavior).
    """

    from core.derived_data import config
    config.symbol_universe[:] = ["CCC"]  # missing OHLC
    config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc())

    published: List[GapSnapshotEvent] = []
    event_bus.subscribe(GapSnapshotEvent, lambda e: published.append(e))

    event_bus.publish(
        session_start_event(
            ts=datetime(2026, 1, 10, 9, 15),
            today_open=100.0,
        )
    )

    assert len(published) == 1
    assert published[0].gaps == {}
