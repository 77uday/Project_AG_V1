# ============================================================
# IMPORTS
# ============================================================
from datetime import datetime


# ============================================================
# CLOCK INTERFACE
# ============================================================
class Clock:
    """
    Base clock interface.
    """
    def now(self) -> datetime:
        raise NotImplementedError


# ============================================================
# REAL CLOCK (LIVE TIME)
# ============================================================
class RealClock(Clock):
    """
    Clock implementation that returns system time.
    """
    def now(self) -> datetime:
        return datetime.now()


# ============================================================
# REPLAY CLOCK (CONTROLLED TIME)
# ============================================================
class ReplayClock(Clock):
    """
    Clock implementation for replay/backtesting.
    Time advances only when explicitly set or advanced.
    """
    def __init__(self, start_time: datetime):
        self._current_time = start_time

    def now(self) -> datetime:
        return self._current_time

    def set(self, new_time: datetime) -> None:
        self._current_time = new_time

    def advance(self, delta) -> None:
        """
        Advance time by a timedelta.
        """
        self._current_time += delta
