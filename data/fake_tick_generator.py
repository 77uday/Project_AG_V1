# ============================================================
# IMPORTS
# ============================================================


import random
from datetime import datetime
from typing import Optional

from core.event_bus import EventBus
from core.clock import Clock
from core.logger import Logger


# ============================================================
# FAKE TICK GENERATOR
# ============================================================

class FakeTickGenerator:
    """
    Deterministic fake tick generator.
    Generates one tick per call.
    """

    def __init__(
        self,
        symbol: str,
        start_price: float,
        event_bus: EventBus,
        clock: Clock,
        logger: Logger,
        seed: Optional[int] = None,
    ):
        self.symbol = symbol
        self._price = start_price
        self._event_bus = event_bus
        self._clock = clock
        self._logger = logger

        self._rng = random.Random(seed)
  
    # ========================================================
    # TICK EMISSION
    # ========================================================

    def emit_tick(self) -> None:
        """
        Generate and emit a single TickEvent.
        """
        timestamp = self._clock.now()

        # Small random price movement
        delta = self._rng.uniform(-1.0, 1.0)
        self._price = max(0.01, self._price + delta)

        tick = {
            "symbol": self.symbol,
            "price": round(self._price, 2),
            "volume": self._rng.randint(1, 100),
            "timestamp": timestamp,
        }

        # Publish event
        self._event_bus.publish("TickEvent", tick)

        # Log event
        self._logger.info(
            "Tick emitted",
            symbol=self.symbol,
            price=tick["price"],
            volume=tick["volume"],
            timestamp=timestamp,
        )
