# ============================================================
# IMPORTS
# ============================================================

from typing import List, Set, Optional, Dict


# ============================================================
# UNIVERSE CONFIG
# ============================================================

symbol_universe: List[str] = []                 # user-provided
manually_omitted_symbols: Optional[Set[str]] = None  # default None


# ============================================================
# SYMBOL METADATA
# ============================================================

symbol_metadata: Dict[str, Dict[str, str]] = {
    # "RELIANCE": {"cap_category": "LARGE"},
}

CAP_PRIORITY = ["LARGE", "MID", "SMALL"]


# ============================================================
# DERIVED DATA CONFIG
# ============================================================

DERIVED_CFG = {
    "threshold_pct": 0.25,        # CPR width threshold (%)
    "top_n": 5,                   # tradable symbols count

    # Target ranges
    "target_step_pct": 0.25,      # %
    "target_max_pct": 20.0,       # %

    # Flip ranges (percent values)
    "flip_steps_pct": [0.0, 0.02, 0.04, 0.05, 0.06, 0.08, 0.10],
}
