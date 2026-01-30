# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass
from datetime import datetime

from core.session.session_context import SessionContext

# ============================================================
# SESSION EVENTS
# ============================================================


@dataclass
class SessionStartEvent:
    """
    Emitted exactly once at the start of each trading session.

    Carries a full SessionContext snapshot so downstream modules
    (Strategy, Analytics, Logger, Replay) remain stateless and
    deterministic.
    """
    timestamp: datetime
    session_context: SessionContext


@dataclass
class SessionEndEvent:
    """
    Emitted exactly once at the end of each trading session.

    The attached SessionContext contains finalized session_end_timestamp
    and previous-day OHLC, making it suitable for archival, logging,
    and replay validation.
    """
    timestamp: datetime
    session_context: SessionContext
