# ============================================================
# IMPORTS
# ============================================================

from datetime import date
from typing import Optional

from core.session.session_context import SessionContext
from core.events.session_events import SessionStartEvent, SessionEndEvent

# ============================================================
# SESSION BOUNDARY DETECTOR
# ============================================================


class SessionBoundaryDetector:
    """
    Detects trading session boundaries from CandleClosedEvent stream.
    Pure timestamp-based logic. Deterministic for Fake / Replay / Live.
    """

    # ========================================================
    # SETUP & WIRING
    # ========================================================
    def __init__(self, event_bus, logger):
        self._event_bus = event_bus
        self._logger = logger

        # active session state
        self._active_session_date: Optional[date] = None
        self._active_session_context: Optional[SessionContext] = None

        # rolling previous-day OHLC (accumulated during a session)
        self._prev_day_open: Optional[float] = None
        self._prev_day_high: Optional[float] = None
        self._prev_day_low: Optional[float] = None
        self._prev_day_close: Optional[float] = None

        # last seen candle timestamp (used to set session_end_timestamp)
        self._last_candle_timestamp = None

        # Wiring: subscribe to CandleClosedEvent
        self._event_bus.subscribe("CandleClosedEvent", self.on_candle_closed)

    # ========================================================
    # CORE DETECTION LOGIC
    # ========================================================
    def on_candle_closed(self, event):
        """
        Core session boundary detection logic.
        Emits SessionStartEvent and SessionEndEvent with full SessionContext
        snapshots. Uses ONLY candle timestamps; deterministic and replay-safe.
        """

        candle_ts = event.timestamp
        candle_date = candle_ts.date()

        candle_open = event.open
        candle_high = event.high
        candle_low = event.low
        candle_close = event.close

        # CASE 1 — first candle ever (bootstrap)
        if self._active_session_date is None:
            self._logger.info(f"[SESSION] First session initialized for {candle_date}")

            # bootstrap previous-day OHLC from first candle
            self._prev_day_open = candle_open
            self._prev_day_high = candle_high
            self._prev_day_low = candle_low
            self._prev_day_close = candle_close

            # set active session
            self._active_session_date = candle_date
            self._active_session_context = SessionContext(
                session_date=candle_date,
                session_start_timestamp=candle_ts,
                session_end_timestamp=None,
                today_open=candle_open,
                prev_day_open=self._prev_day_open,
                prev_day_high=self._prev_day_high,
                prev_day_low=self._prev_day_low,
                prev_day_close=self._prev_day_close,
            )

            # publish SessionStartEvent for the first session
            self._event_bus.publish(
                SessionStartEvent(timestamp=candle_ts, session_context=self._active_session_context)
            )
            self._logger.info(f"[SESSION] Session started: {candle_date}")

            self._last_candle_timestamp = candle_ts
            return

        # CASE 2 — same session (just update rolling OHLC candidate)
        if candle_date == self._active_session_date:
            # rolling update for previous-day OHLC candidate
            # note: prev_day_* were seeded at session start (bootstrap or previous)
            self._prev_day_high = max(self._prev_day_high, candle_high)
            self._prev_day_low = min(self._prev_day_low, candle_low)
            self._prev_day_close = candle_close

            self._last_candle_timestamp = candle_ts
            return

        # CASE 3 — new session detected (date has changed)
        self._logger.info(
            f"[SESSION] Session change detected: {self._active_session_date} → {candle_date}"
        )

        # finalize previous session end timestamp (last seen candle of previous session)
        self._active_session_context.session_end_timestamp = self._last_candle_timestamp

        # publish SessionEndEvent with the finalized previous session context
        self._event_bus.publish(
            SessionEndEvent(timestamp=self._last_candle_timestamp, session_context=self._active_session_context)
        )
        self._logger.info(f"[SESSION] Session ended: {self._active_session_date}")

        # freeze previous-day OHLC (these values are the final prev-day OHLC for the new session)
        prev_open = self._prev_day_open
        prev_high = self._prev_day_high
        prev_low = self._prev_day_low
        prev_close = self._prev_day_close

        # start new session context using the current candle as the open of the new session
        self._active_session_date = candle_date
        self._active_session_context = SessionContext(
            session_date=candle_date,
            session_start_timestamp=candle_ts,
            session_end_timestamp=None,
            today_open=candle_open,
            prev_day_open=prev_open,
            prev_day_high=prev_high,
            prev_day_low=prev_low,
            prev_day_close=prev_close,
        )

        # publish SessionStartEvent with the new session context
        self._event_bus.publish(
            SessionStartEvent(timestamp=candle_ts, session_context=self._active_session_context)
        )
        self._logger.info(f"[SESSION] Session started: {candle_date}")

        # reset rolling OHLC accumulation to begin tracking the new session's candidate values
        self._prev_day_open = candle_open
        self._prev_day_high = candle_high
        self._prev_day_low = candle_low
        self._prev_day_close = candle_close

        self._last_candle_timestamp = candle_ts
