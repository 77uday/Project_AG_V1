import pytest
from datetime import datetime, timezone, date, timedelta

# imports from your project
from core.derived_data.derived_data_store import InMemoryDerivedDataStore
from core.derived_data.derived_data_processor import DerivedDataProcessor
from core.derived_data import config as derived_config
from core.events.session_events import SessionStartEvent
from core.session.session_context import SessionContext


# ============================================================
# Simple test EventBus and Logger (local to tests)
# ============================================================

class TestEventBus:
    def __init__(self):
        # key: event class -> list of handlers
        self._subs = {}

    def subscribe(self, event_key, handler):
        handlers = self._subs.setdefault(event_key, [])
        handlers.append(handler)

    def publish(self, event):
        # dispatch to any subscriber whose key is class and event is instance of key
        for key, handlers in list(self._subs.items()):
            try:
                if isinstance(event, key):
                    for h in handlers:
                        h(event)
            except Exception:
                # key might be string-based; also allow exact match on type equality
                if key == type(event):
                    for h in handlers:
                        h(event)


class TestLogger:
    def __init__(self):
        self.records = []

    def info(self, *args, **kwargs):
        # store tuples for assertions if needed
        self.records.append((args, kwargs))


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def event_bus():
    return TestEventBus()


@pytest.fixture
def logger():
    return TestLogger()


@pytest.fixture
def store():
    return InMemoryDerivedDataStore()


@pytest.fixture
def processor(event_bus, logger, store):
    # create processor with test bus/logger/store
    return DerivedDataProcessor(event_bus=event_bus, logger=logger, store=store)


# ============================================================
# Helper: sample prev_day_ohlc
# ============================================================

def prev_day_ohlc_sample():
    """
    Construct prev-day OHLC that yields:
    - AAA: narrow CPR width (should be first)
    - BBB: wider CPR width (should be second)
    - CCC: missing
    """
    return {
        "AAA": {"high": 110.0, "low": 90.0, "close": 100.0},   # narrow (width ~0)
        "BBB": {"high": 150.0, "low": 50.0, "close": 120.0},   # wide CPR
        # "CCC" intentionally missing
    }


# ============================================================
# TESTS
# ============================================================

def test_pre_market_builds_filtered_and_tradable(processor, store, event_bus, logger):
    """
    Verifies:
    - symbols_missing_prev_day_ohlc is tracked
    - filtered_symbols sorted by CPR width (ascending)
    - tradable_symbols selected by threshold + top-N
    - per-symbol data persisted and helpers work
    """

    # Override universe for this test
    derived_config.symbol_universe[:] = ["AAA", "BBB", "CCC"]
    derived_config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc_sample())

    # snapshot persisted
    assert len(store.universe_snapshots) == 1
    snap = store.universe_snapshots[0]

    # CCC missing OHLC → excluded but tracked
    assert "CCC" in snap.symbols_missing_prev_day_ohlc
    assert "CCC" not in snap.filtered_symbols

    # Filtered symbols should include AAA, BBB
    assert set(snap.filtered_symbols) == {"AAA", "BBB"}

    # CPR width check (AAA should be tighter than BBB here)
    # So AAA should appear before BBB
    assert snap.filtered_symbols[0] == "AAA"

    # tradable symbols length (top_n default from config)
    assert isinstance(snap.tradable_symbols, list)

    # symbol-level persisted data exists and helpers work
    a_data = store.get_symbol_data("AAA")
    assert a_data is not None
    assert len(a_data.target_range_pos) > 1
    # step index 2 exists (0-based)
    tp = store.get_target_by_step("AAA", 2, side="pos")
    assert tp == a_data.target_range_pos[2]
    flip = store.get_flip_for_step("AAA", 0, side="pos")
    assert flip == a_data.flip_range_pos[0]
    sl = store.get_stop_for_step("AAA", 2, side="pos")
    assert sl is not None


def test_pre_market_is_deterministic(processor, store):
    """
    Running pre-market twice yields stable snapshots (same order)
    """
    derived_config.symbol_universe[:] = ["AAA", "BBB", "CCC"]
    derived_config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc_sample())
    first = store.universe_snapshots[-1]

    # run again with same input
    processor.run_pre_market(prev_day_ohlc_sample())
    second = store.universe_snapshots[-1]

    assert first.tradable_symbols == second.tradable_symbols
    assert first.filtered_symbols == second.filtered_symbols


def test_gap_snapshot_emitted_on_session_start(processor, store):
    """
    After pre-market, session start with today_open must emit gap snapshot
    for tradable symbols.
    """
    derived_config.symbol_universe[:] = ["AAA", "BBB", "CCC"]
    derived_config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc_sample())

    # Build SessionStartEvent with today_open value (take AAA prev_close + small change)
    from datetime import datetime, timezone
    from core.session.session_context import SessionContext

    now = datetime.now(timezone.utc)
    session_ctx = SessionContext(
        session_date=now.date(),
        session_start_timestamp=now,
        session_end_timestamp=None,
        today_open=101.0,  # opening price used for gap calc
        prev_day_open=None,
        prev_day_high=None,
        prev_day_low=None,
        prev_day_close=None,
    )

    session_event = SessionStartEvent(timestamp=now, session_context=session_ctx)

    # publish event (this should be received by processor and gap snapshot stored)
    processor._event_bus.publish(session_event)

    assert len(store.gap_snapshots) == 1
    gap = store.gap_snapshots[0]
    assert "AAA" in gap.gaps or "BBB" in gap.gaps


def test_no_gap_emitted_when_no_tradables(processor, store):
    """
    If no tradables (e.g., missing prev-day OHLC), session start should not emit gap snapshot.
    """
    # set universe to a symbol with no prev-day data
    derived_config.symbol_universe[:] = ["X1"]
    derived_config.manually_omitted_symbols = None

    processor.run_pre_market(prev_day_ohlc={})  # no prev-day OHLC at all

    from datetime import datetime, timezone
    from core.session.session_context import SessionContext
    now = datetime.now(timezone.utc)
    session_ctx = SessionContext(
        session_date=now.date(),
        session_start_timestamp=now,
        session_end_timestamp=None,
        today_open=10.0,
        prev_day_open=None,
        prev_day_high=None,
        prev_day_low=None,
        prev_day_close=None,
    )
    session_event = SessionStartEvent(timestamp=now, session_context=session_ctx)

    processor._event_bus.publish(session_event)

    # no gap snapshots should be created
    assert len(store.gap_snapshots) == 0

# ============================================================
# HELPER FUNCTION TESTS (DerivedDataStore)
# ============================================================

def test_get_target_by_step(store):
    """
    Ensures target_range_pos and target_range_neg
    return correct absolute price levels.
    """

    from core.derived_data.models import DerivedSymbolData

    prev_close = 100.0

    record = DerivedSymbolData(
        symbol="AAA",
        prev_high=105.0,
        prev_low=95.0,
        prev_close=prev_close,
        P=100.0,
        BC=99.0,
        TC=101.0,
        cpr_width_pct=0.2,
        target_range_pos=[100.0, 100.25, 100.5],
        target_range_neg=[100.0, 99.75, 99.5],
        flip_range_pos=[],
        flip_range_neg=[],
        metadata={},
    )

    store.persist_symbol_data(record)

    assert store.get_target_by_step("AAA", 1, "pos") == 100.25
    assert store.get_target_by_step("AAA", 2, "neg") == 99.5
    assert store.get_target_by_step("AAA", 5, "pos") is None


def test_get_flip_for_step(store):
    """
    Ensures flip ranges return correct levels.
    """

    from core.derived_data.models import DerivedSymbolData

    prev_close = 100.0

    record = DerivedSymbolData(
        symbol="BBB",
        prev_high=105.0,
        prev_low=95.0,
        prev_close=prev_close,
        P=100.0,
        BC=99.0,
        TC=101.0,
        cpr_width_pct=0.2,
        target_range_pos=[],
        target_range_neg=[],
        flip_range_pos=[100.0, 100.02, 100.04],
        flip_range_neg=[100.0, 99.98, 99.96],
        metadata={},
    )

    store.persist_symbol_data(record)

    assert store.get_flip_for_step("BBB", 1, "pos") == 100.02
    assert store.get_flip_for_step("BBB", 2, "neg") == 99.96
    assert store.get_flip_for_step("BBB", 10, "pos") is None


def test_get_stop_for_step(store):
    """
    Stop price must be symmetric relative to prev_close.
    Example:
        prev_close = 100
        target_pos step = 100.25 (+0.25%)
        stop should be 99.75 (-0.25%)
    """

    from core.derived_data.models import DerivedSymbolData

    prev_close = 100.0

    record = DerivedSymbolData(
        symbol="CCC",
        prev_high=105.0,
        prev_low=95.0,
        prev_close=prev_close,
        P=100.0,
        BC=99.0,
        TC=101.0,
        cpr_width_pct=0.2,
        target_range_pos=[100.0, 100.25],
        target_range_neg=[100.0, 99.75],
        flip_range_pos=[],
        flip_range_neg=[],
        metadata={},
    )

    store.persist_symbol_data(record)

    # LONG case
    stop_long = store.get_stop_for_step("CCC", 1, "pos")
    assert round(stop_long, 2) == 99.75

    # SHORT case
    stop_short = store.get_stop_for_step("CCC", 1, "neg")
    assert round(stop_short, 2) == 100.25

    # Out-of-range safety
    assert store.get_stop_for_step("CCC", 10, "pos") is None
