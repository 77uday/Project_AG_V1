# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, date

# ============================================================
# DERIVED SYMBOL DATA
# ============================================================

@dataclass
class DerivedSymbolData:
    """
    Per-symbol derived snapshot computed pre-market.

    - target_range_pos / neg: list of absolute price levels (index => step_index).
    - flip_range_pos / neg: list of absolute price levels (index => flip step index).
    - prev_close is kept for reference and for stop-price derivation helpers.
    - metadata: operator-editable dictionary (cap category, lot_size, etc.)
    """
    symbol: str
    prev_high: float
    prev_low: float
    prev_close: float

    P: float
    BC: float
    TC: float
    cpr_width_pct: float

    target_range_pos: List[float] = field(default_factory=list)
    target_range_neg: List[float] = field(default_factory=list)
    flip_range_pos: List[float] = field(default_factory=list)
    flip_range_neg: List[float] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================================
# SNAPSHOT / EVENTS (lightweight outline)
# ============================================================

@dataclass
class DerivedUniverseSnapshot:
    timestamp: datetime
    effective_universe: List[str]
    filtered_symbols: List[str]
    tradable_symbols: List[str]
    symbols_missing_prev_day_ohlc: List[str]


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
