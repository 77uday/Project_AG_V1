# ============================================================
# IMPORTS
# ============================================================

from typing import Iterable, Dict

from core.event_bus import EventBus
from core.clock import ReplayClock
from core.logger import Logger

# ============================================================
# REPLAY LOADER
# ============================================================

class ReplayLoader:
    """
    Replays recorded tick data into the EventBus.
    """

    def __init__(
        self,
        ticks: Iterable[Dict],
        event_bus: EventBus,
        clock: ReplayClock,
        logger: Logger,
    ):
        self._ticks = ticks
        self._event_bus = event_bus
        self._clock = clock
        self._logger = logger

    # ========================================================
    # REPLAY API
    # ========================================================

    def replay_next(self) -> bool:
        """
        Replay the next tick.
        Returns False when replay is finished.
        """
        try:
            tick = next(self._ticks)
        except StopIteration:
            self._logger.info("Replay finished")
            return False

        # Drive the clock using recorded timestamp
        self._clock.set(tick["timestamp"])

        # Emit the tick event
        self._event_bus.publish("TickEvent", tick)

        # Log replay action
        self._logger.info(
            "Tick replayed",
            symbol=tick["symbol"],
            price=tick["price"],
            volume=tick["volume"],
            timestamp=tick["timestamp"],
        )

        return True
