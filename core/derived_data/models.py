# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Set, Any

from core.session.session_context import SessionContext


# ============================================================
# DERIVED DATA PER SYMBOL (INTERNAL STRUCT)
# ============================================================

@dataclass
class DerivedSymbolData:
    symbol: str
    prev_high: float
    prev_low: float
    prev_close: float

    P: float
    BC: float
    TC: float
    cpr_width_pct: float

    target_range_pos: List[float]
    target_range_neg: List[float]

    flip_range_pos: List[float]
    flip_range_neg: List[float]

    metadata: Dict[str, Any]


# ============================================================
# EVENTS
# ============================================================

@dataclass
class DerivedDataEvent:
    timestamp: datetime
    symbol: str
    timeframe: str
    derived: DerivedSymbolData
    session_context: Optional[SessionContext]


@dataclass
class DerivedUniverseSnapshot:
    timestamp: datetime

    effective_universe: List[str]
    filtered_symbols: List[str]
    tradable_symbols: List[str]

    symbols_missing_prev_day_ohlc: Set[str]


@dataclass
class GapSnapshotEvent:
    timestamp: datetime
    gaps: Dict[str, Dict[str, float]]
    # example:
    # {
    #   "RELIANCE": {
    #       "prev_close": 2450.0,
    #       "today_open": 2462.0,
    #       "gap_pct": 0.49,
    #       "gap_pct_abs": 0.49
    #   }
    # }
