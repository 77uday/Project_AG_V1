# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

# ============================================================
# SESSION CONTEXT (DATA MODEL)
# ============================================================


@dataclass
class SessionContext:
    """
    Immutable snapshot of a trading session's contextual data.

    Used for:
    - Session boundary awareness
    - CPR calculation
    - Gap up / gap down detection
    - Deterministic replay & logging
    """

    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------
    session_date: date

    # --------------------------------------------------------
    # TIMING
    # --------------------------------------------------------
    session_start_timestamp: datetime
    session_end_timestamp: Optional[datetime]

    # --------------------------------------------------------
    # TODAY (CURRENT SESSION)
    # --------------------------------------------------------
    today_open: float

    # --------------------------------------------------------
    # PREVIOUS SESSION (FINALIZED OHLC)
    # --------------------------------------------------------
    prev_day_open: float
    prev_day_high: float
    prev_day_low: float
    prev_day_close: float
