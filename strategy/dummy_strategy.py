# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from strategy.intent_events import IntentEvent, TriggerSpec, Side
from core.derived_data.models import GapSnapshotEvent
from core.derived_data.derived_data_store import DerivedDataStore

# OrderFillEvent may live in core.events.order_events (if present).
# Handler below is defensive: if import fails, we still run (no fill-handling).
try:
    from core.events.order_events import OrderFillEvent
except Exception:
    OrderFillEvent = None  # type: ignore

from core.events.session_events import SessionEndEvent


# ============================================================
# DUMMY STRATEGY (Pattern B) - Intent-per-step, event-driven
# ============================================================

class DummyStrategy:
    """
    Minimal Pattern-B Strategy (dummy implementation).

    Responsibilities (strict):
    - Subscribe to GapSnapshotEvent (preference ordering at open)
    - Select 1 symbol (least absolute gap) from the gap snapshot
    - Maintain step_index (1-based)
    - Emit one IntentEvent per step containing BOTH triggers (LONG & SHORT)
    - On OrderFillEvent matching active intent -> auto-advance (emit next IntentEvent)
    - On SessionEndEvent -> deactivate

    Strictly does NOT:
    - Read tick stream
    - Place orders
    - Apply risk rules (only emits IntentEvent)
    """

    # ========================================================
    # SETUP & WIRING
    # ========================================================

    def __init__(
        self,
        event_bus,
        logger,
        store: DerivedDataStore,
        strategy_id: str = "DUMMY",
        auto_advance: bool = True,
        initial_step: int = 1,
        flip_timeout_seconds: int = 60,
    ):
        self._bus = event_bus
        self._log = logger
        self._store = store
        self._id = strategy_id

        # runtime state
        self._active_symbol: Optional[str] = None
        self._step_index: int = initial_step
        self._active_intent_id: Optional[str] = None
        self._active: bool = True
        self._auto_advance = auto_advance
        self._flip_timeout_seconds = flip_timeout_seconds

        # Subscribe to events
        self._bus.subscribe(GapSnapshotEvent, self._on_gap_snapshot)
        if OrderFillEvent is not None:
            self._bus.subscribe(OrderFillEvent, self._on_order_fill)
        self._bus.subscribe(SessionEndEvent, self._on_session_end)

        self._log.info("[STRATEGY] DummyStrategy initialized", strategy_id=self._id)

    # ========================================================
    # CORE INTENT BUILDING
    # ========================================================

    def _make_intent_id(self, symbol: str, step_index: int) -> str:
        ts = datetime.now(timezone.utc).isoformat()
        return f"{self._id}:{symbol}:step{step_index}:{ts}"

    def _build_intent(self, symbol: str, step_index: int) -> IntentEvent:
        """
        Build IntentEvent containing both LONG and SHORT triggers for the given step_index.
        """
        triggers = [
            TriggerSpec(side=Side.LONG, step_index=step_index, timeout_seconds=self._flip_timeout_seconds),
            TriggerSpec(side=Side.SHORT, step_index=step_index, timeout_seconds=self._flip_timeout_seconds),
        ]

        intent = IntentEvent(
            intent_id=self._make_intent_id(symbol, step_index),
            strategy_id=self._id,
            symbol=symbol,
            triggers=triggers,
            auto_advance=self._auto_advance,
            created_at=datetime.now(timezone.utc),
            correlation_id=None,
            session_date=None,
        )
        return intent

    def _publish_intent(self, intent: IntentEvent) -> None:
        # Publish raw IntentEvent (RiskManager is expected to pick up, approve, etc.)
        self._bus.publish(intent)
        self._active_intent_id = intent.intent_id
        self._log.info("[STRATEGY] Intent emitted", intent_id=intent.intent_id, symbol=intent.symbol, step_index=intent.triggers[0].step_index)

    # ========================================================
    # EVENT HANDLERS
    # ========================================================

    def _on_gap_snapshot(self, event: GapSnapshotEvent) -> None:
        """
        Called at market-open gap snapshot.
        event.gaps: Dict[symbol -> {prev_close, today_open, gap_pct, gap_pct_abs}]
        Strategy picks the least gap_pct_abs among provided gaps and emits initial Intent.
        """
        if not self._active:
            self._log.info("[STRATEGY] Received GapSnapshot but strategy is inactive.")
            return

        if not event.gaps:
            self._log.info("[STRATEGY] GapSnapshot empty; no action.")
            return

        # pick symbol with smallest absolute gap
        try:
            sorted_syms = sorted(event.gaps.items(), key=lambda kv: kv[1].get("gap_pct_abs", float("inf")))
            chosen_symbol = sorted_syms[0][0]
        except Exception as e:
            self._log.info("[STRATEGY] Error selecting symbol from gap snapshot", error=str(e))
            return

        # set active symbol and reset step_index to initial (1)
        self._active_symbol = chosen_symbol
        self._step_index = 1

        intent = self._build_intent(chosen_symbol, self._step_index)
        self._publish_intent(intent)

    def _on_order_fill(self, event: Any) -> None:
        """
        Handle OrderFillEvent (structure varies by adapter).
        We attempt to extract an intent id from event and check if it matches active intent.
        If so — advance step (if auto_advance) and emit next IntentEvent.
        """
        if not self._active or not self._active_intent_id:
            return

        # extract intent id robustly
        intent_id = None
        # common shapes:
        if hasattr(event, "intent_id"):
            intent_id = getattr(event, "intent_id")
        elif hasattr(event, "origin_intent_id"):
            intent_id = getattr(event, "origin_intent_id")
        elif hasattr(event, "intent") and getattr(event, "intent") is not None:
            nested = getattr(event, "intent")
            intent_id = getattr(nested, "intent_id", None)

        if intent_id != self._active_intent_id:
            # not related to our current active intent
            return

        # Advance to next step if requested
        if self._auto_advance:
            if self._active_symbol is None:
                self._log.info("[STRATEGY] Fill matched intent but no active_symbol found.")
                return

            self._step_index += 1
            next_intent = self._build_intent(self._active_symbol, self._step_index)
            self._publish_intent(next_intent)
        else:
            self._log.info("[STRATEGY] Fill matched intent but auto_advance disabled; stopping progression.")

    def _on_session_end(self, event: SessionEndEvent) -> None:
        # deactivate and clear state
        self._active = False
        prev = self._active_symbol
        self._active_symbol = None
        self._active_intent_id = None
        self._log.info("[STRATEGY] Session ended, strategy deactivated", previous_symbol=prev)


# ============================================================
# FACTORY
# ============================================================

def create_dummy_strategy(event_bus, logger, store: DerivedDataStore, strategy_id: str = "DUMMY") -> DummyStrategy:
    """
    Convenience factory used by tests or app wiring.
    """
    return DummyStrategy(event_bus=event_bus, logger=logger, store=store, strategy_id=strategy_id)
