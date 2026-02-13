# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime, timezone
from typing import Dict, List, Set

from core.event_bus import EventBus
from core.logger import Logger

from core.derived_data.config import (
    symbol_universe,
    manually_omitted_symbols,
    symbol_metadata,
    CAP_PRIORITY,
    DERIVED_CFG,
)

from core.derived_data.models import (
    DerivedSymbolData,
    DerivedDataEvent,
    DerivedUniverseSnapshot,
    GapSnapshotEvent,
)

from core.derived_data.derived_data_store import DerivedDataStore
from core.events.session_events import SessionStartEvent


# ============================================================
# DERIVED DATA PROCESSOR
# ============================================================

class DerivedDataProcessor:
    """
    Computes derived market data from previous-day candles
    and session open prices.

    Deterministic. Replay-safe. No strategy logic.
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

        self._effective_universe: List[str] = []
        self._symbols_missing_prev_day_ohlc: Set[str] = set()

        self._filtered_records: List[DerivedSymbolData] = []
        self._tradable_records: List[DerivedSymbolData] = []

        # Subscribe to session start for gap snapshot
        self._event_bus.subscribe(SessionStartEvent, self._on_session_start)

    # ========================================================
    # UNIVERSE MANAGEMENT
    # ========================================================

    def universe_refresh(self) -> None:
        """
        Reload symbol_universe and manually_omitted_symbols.
        Preserve the order of symbol_universe so stable sorts remain deterministic.
        """
        omitted = set(manually_omitted_symbols or set())
        # preserve symbol_universe order and filter omitted
        self._effective_universe = [s for s in symbol_universe if s not in omitted]

        self._logger.info(
            "[DERIVED] Universe refreshed",
            effective_count=len(self._effective_universe),
        )

    # ========================================================
    # PRE-MARKET CORE LOGIC
    # ========================================================

    def _compute_cpr(self, h: float, l: float, c: float):
        P = (h + l + c) / 3.0
        BC = (h + l) / 2.0
        TC = 2 * P - BC
        width_pct = abs(TC - BC) / P * 100.0
        return P, BC, TC, width_pct

    def _compute_target_ranges(self, x: float):
        step = DERIVED_CFG["target_step_pct"] / 100.0
        max_k = DERIVED_CFG["target_max_pct"] / 100.0

        ks = []
        k = 0.0
        # ensure numeric stability: build by integer steps
        num_steps = int(round((DERIVED_CFG["target_max_pct"] / DERIVED_CFG["target_step_pct"]))) + 1
        for i in range(num_steps):
            ks.append(i * step)

        pos = [x * (1 + k) for k in ks]
        neg = [x * (1 - k) for k in ks]
        return pos, neg

    def _compute_flip_ranges(self, x: float):
        ks = [k / 100.0 for k in DERIVED_CFG["flip_steps_pct"]]
        pos = [x * (1 + k) for k in ks]
        neg = [x * (1 - k) for k in ks]
        return pos, neg

    def run_pre_market(self, prev_day_ohlc: Dict[str, Dict[str, float]]) -> None:
        """
        prev_day_ohlc format:
        {
            "RELIANCE": {"high":..., "low":..., "close":...},
            ...
        }
        """

        self.universe_refresh()
        self._symbols_missing_prev_day_ohlc.clear()
        self._filtered_records.clear()
        self._tradable_records.clear()

        for symbol in self._effective_universe:
            ohlc = prev_day_ohlc.get(symbol)
            if not ohlc:
                self._symbols_missing_prev_day_ohlc.add(symbol)
                continue

            h, l, c = ohlc["high"], ohlc["low"], ohlc["close"]

            P, BC, TC, width_pct = self._compute_cpr(h, l, c)
            target_pos, target_neg = self._compute_target_ranges(c)
            flip_pos, flip_neg = self._compute_flip_ranges(c)

            record = DerivedSymbolData(
                symbol=symbol,
                prev_high=h,
                prev_low=l,
                prev_close=c,
                P=P,
                BC=BC,
                TC=TC,
                cpr_width_pct=width_pct,
                target_range_pos=target_pos,
                target_range_neg=target_neg,
                flip_range_pos=flip_pos,
                flip_range_neg=flip_neg,
                metadata=symbol_metadata.get(symbol, {}),
            )

            # persist per-symbol derived data into store (new)
            try:
                self._store.persist_symbol_data(record)
            except Exception as e:
                # defensive: log but continue building the in-memory list
                self._logger.info("[DERIVED] Failed to persist symbol data", symbol=symbol, error=str(e))

            self._filtered_records.append(record)

        # Sort by CPR width, stable
        self._filtered_records.sort(key=lambda r: r.cpr_width_pct)

        # Apply threshold + top-N
        threshold = DERIVED_CFG["threshold_pct"]
        top_n = DERIVED_CFG["top_n"]

        candidates = [
            r for r in self._filtered_records
            if r.cpr_width_pct < threshold
        ]

        self._tradable_records = candidates[:top_n]

        snapshot = DerivedUniverseSnapshot(
            timestamp=datetime.now(timezone.utc),
            effective_universe=self._effective_universe,
            filtered_symbols=[r.symbol for r in self._filtered_records],
            tradable_symbols=[r.symbol for r in self._tradable_records],
            symbols_missing_prev_day_ohlc=list(self._symbols_missing_prev_day_ohlc),
        )

        # persist snapshot and publish as before
        self._store.persist_universe_snapshot(snapshot)
        self._event_bus.publish(snapshot)

        self._logger.info(
            "[DERIVED] Pre-market snapshot emitted",
            tradable=len(self._tradable_records),
            missing=len(self._symbols_missing_prev_day_ohlc),
        )

    # ========================================================
    # MARKET OPEN (GAP LOGIC)
    # ========================================================

    def _on_session_start(self, event: SessionStartEvent) -> None:
        """
        At session start (e.g. 09:15) — compute gap up/down for tradable symbols.

        Only publish gap snapshot when there are tradable symbols.
        """

        if not self._tradable_records:
            self._logger.info("[DERIVED] No tradables at session start; skipping gap snapshot.")
            return

        gaps: Dict[str, Dict[str, float]] = {}

        for record in self._tradable_records:
            prev_close = record.prev_close
            today_open = event.session_context.today_open

            gap_pct = ((today_open - prev_close) / prev_close) * 100.0
            gaps[record.symbol] = {
                "prev_close": prev_close,
                "today_open": today_open,
                "gap_pct": gap_pct,
                "gap_pct_abs": abs(gap_pct),
            }

        if not gaps:
            self._logger.info("[DERIVED] No gap data computed; skipping emit.")
            return

        gap_event = GapSnapshotEvent(
            timestamp=event.timestamp,
            gaps=gaps,
        )

        self._store.persist_gap_snapshot(gap_event)
        self._event_bus.publish(gap_event)

        self._logger.info(
            "[DERIVED] Gap snapshot emitted",
            symbols=len(gaps),
        )
