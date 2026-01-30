# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime, timedelta
from typing import Dict, Optional

from core.event_bus import EventBus
from core.logger import Logger

# ============================================================
# CANDLE BUILDER
# ============================================================

class CandleBuilder:
    """
    Builds 1-minute OHLCV candles from TickEvent data.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: Logger,
        timeframe: timedelta = timedelta(minutes=1),
    ):
        self._event_bus = event_bus
        self._logger = logger
        self._timeframe = timeframe
        # key: symbol -> current candle
        self._current_candles: Dict[str, Dict] = {}

        # Subscribe to TickEvent
        self._event_bus.subscribe("TickEvent", self._on_tick)


    # ========================================================
    # CORE CANDLE LOGIC
    # ========================================================

    def process_tick(self, tick: Dict) -> Dict[str, Optional[Dict]]:
        """
        Process a single tick and update candle state.

        Returns:
            {
              "update": current candle (after update),
              "closed": closed candle (if any, else None)
            }
        """
        symbol = tick["symbol"]
        price = tick["price"]
        volume = tick["volume"]
        timestamp: datetime = tick["timestamp"]

        candle_start = timestamp.replace(second=0, microsecond=0)
        candle_end = candle_start + self._timeframe

        closed_candle = None

        current = self._current_candles.get(symbol)

        # Case 1: No candle yet → start new candle
        if current is None:
            current = {
                "symbol": symbol,
                "timeframe": "1m",
                "start_time": candle_start,
                "end_time": candle_end,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
            self._current_candles[symbol] = current
            return {"update": current, "closed": None}

        # Case 2: Tick belongs to current candle
        if timestamp < current["end_time"]:
            current["high"] = max(current["high"], price)
            current["low"] = min(current["low"], price)
            current["close"] = price
            current["volume"] += volume
            return {"update": current, "closed": None}

        # Case 3: Tick belongs to next candle → close current
        closed_candle = current

        new_candle = {
            "symbol": symbol,
            "timeframe": "1m",
            "start_time": candle_start,
            "end_time": candle_end,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
        }

        self._current_candles[symbol] = new_candle

        return {
            "update": new_candle,
            "closed": closed_candle,
        }
    
    # ========================================================
    # EVENT HANDLER
    # ========================================================

    def _on_tick(self, tick: Dict) -> None:
        """
        Handle incoming TickEvent.
        """
        result = self.process_tick(tick)

        # Emit candle update event
        update = result["update"]
        self._event_bus.publish("CandleUpdateEvent", update)

        # Emit candle closed event if present
        closed = result["closed"]
        if closed:
            self._event_bus.publish("CandleClosedEvent", closed)

            self._logger.info(
                "Candle closed",
                symbol=closed["symbol"],
                timeframe=closed["timeframe"],
                start_time=closed["start_time"],
                end_time=closed["end_time"],
                open=closed["open"],
                high=closed["high"],
                low=closed["low"],
                close=closed["close"],
                volume=closed["volume"],
            )
 