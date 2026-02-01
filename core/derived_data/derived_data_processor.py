# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime
from typing import Set

from core.event_bus import EventBus
from core.logger import Logger

from core.events.candle_events import CandleClosedEvent
from core.events.session_events import SessionStartEvent

from core.derived_data.config import (
    symbol_universe,
    manually_omitted_symbols,
)
from core.derived_data.models import (
    DerivedUniverseSnapshot,
    GapSnapshotEvent,
)
from core.derived_data.derived_data_store import DerivedDataStore


# ============================================================
# DERIVED DATA PROCESSOR
# ============================================================

class DerivedDataProcessor:
    """
    Converts candles + session data into derived market inputs.
    """

    # ========================================================
    # SETUP & WIRING
    # ========================================================

    def __init__(
        self,
        event_bus: EventBus,
        logger: Logger,
        store: DerivedDataStore,
    ):
        self._event_bus = event_bus
        self._logger = logger
        self._store = store

        self._effective_universe: Set[str] = set()
        self._symbols_missing_prev_day_ohlc: Set[str] = set()

        self._event_bus.subscribe("CandleClosedEvent", self._on_candle_closed)
        self._event_bus.subscribe(SessionStartEvent, self._on_session_start)

    # ========================================================
    # UNIVERSE MANAGEMENT
    # ========================================================

    def universe_refresh(self) -> None:
        """
        Reload symbol_universe and manually_omitted_symbols.
        Intended to be called at market open (9:15).
        """
        omitted = manually_omitted_symbols or set()
        self._effective_universe = set(symbol_universe) - omitted

        self._logger.info(
            "[DERIVED] Universe refreshed",
            effective_count=len(self._effective_universe),
        )

    # ========================================================
    # EVENT HANDLERS (SKELETON)
    # ========================================================

    def _on_candle_closed(self, event: CandleClosedEvent) -> None:
        """
        Pre-market & intraday derived computations.
        (Actual math added in STEP-3)
        """
        pass

    def _on_session_start(self, event: SessionStartEvent) -> None:
        """
        Market open logic (9:15):
        - universe_refresh
        - gap calculations
        """
        self.universe_refresh()
        pass
