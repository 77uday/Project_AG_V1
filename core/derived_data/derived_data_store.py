# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime
from typing import Dict, List, Optional

from core.derived_data.models import DerivedSymbolData, DerivedUniverseSnapshot, GapSnapshotEvent

# ============================================================
# STORAGE INTERFACE / IN-MEMORY IMPLEMENTATION
# ============================================================

class DerivedDataStore:
    """
    Interface / contract for storing derived-data artifacts.
    Implement persistent variant (DB / files) later; InMemory used for tests/dev.
    """

    def persist_symbol_data(self, symbol_data: DerivedSymbolData) -> None:
        raise NotImplementedError

    def get_symbol_data(self, symbol: str) -> Optional[DerivedSymbolData]:
        raise NotImplementedError

    def persist_universe_snapshot(self, snapshot: DerivedUniverseSnapshot) -> None:
        raise NotImplementedError

    def persist_gap_snapshot(self, gap_event: GapSnapshotEvent) -> None:
        raise NotImplementedError

    # helpers
    def get_target_by_step(self, symbol: str, step_index: int, side: str = "pos") -> Optional[float]:
        raise NotImplementedError

    def get_flip_for_step(self, symbol: str, step_index: int, side: str = "pos") -> Optional[float]:
        raise NotImplementedError

    def get_stop_for_step(self, symbol: str, step_index: int, side: str = "pos") -> Optional[float]:
        raise NotImplementedError


class InMemoryDerivedDataStore(DerivedDataStore):
    """
    Simple in-memory store used by tests and local dev.
    """

    def __init__(self):
        # symbol -> DerivedSymbolData
        self._symbols: Dict[str, DerivedSymbolData] = {}

        # snapshots history (kept for audit/replay)
        self.universe_snapshots: List[DerivedUniverseSnapshot] = []
        self.gap_snapshots: List[GapSnapshotEvent] = []

    # ---------------------------
    # persistence
    # ---------------------------

    def persist_symbol_data(self, symbol_data: DerivedSymbolData) -> None:
        self._symbols[symbol_data.symbol] = symbol_data

    def get_symbol_data(self, symbol: str) -> Optional[DerivedSymbolData]:
        return self._symbols.get(symbol)

    def persist_universe_snapshot(self, snapshot: DerivedUniverseSnapshot) -> None:
        self.universe_snapshots.append(snapshot)

    def persist_gap_snapshot(self, gap_event: GapSnapshotEvent) -> None:
        self.gap_snapshots.append(gap_event)

    # ---------------------------
    # helpers (accessors)
    # ---------------------------

    def get_target_by_step(self, symbol: str, step_index: int, side: str = "pos") -> Optional[float]:
        record = self.get_symbol_data(symbol)
        if not record:
            return None
        if side == "pos":
            if 0 <= step_index < len(record.target_range_pos):
                return record.target_range_pos[step_index]
        else:
            if 0 <= step_index < len(record.target_range_neg):
                return record.target_range_neg[step_index]
        return None

    def get_flip_for_step(self, symbol: str, step_index: int, side: str = "pos") -> Optional[float]:
        record = self.get_symbol_data(symbol)
        if not record:
            return None
        if side == "pos":
            if 0 <= step_index < len(record.flip_range_pos):
                return record.flip_range_pos[step_index]
        else:
            if 0 <= step_index < len(record.flip_range_neg):
                return record.flip_range_neg[step_index]
        return None

    def get_stop_for_step(self, symbol: str, step_index: int, side: str = "pos") -> Optional[float]:
        """
        Compute stop price for an entry on the given step:
        - For LONG (pos): stop is symmetric opposite of the target percentage relative to prev_close,
          i.e., if target_pct = (target_price/prev_close - 1), stop_price = prev_close * (1 - target_pct)
        - For SHORT (neg): symmetric: if target_price = prev_close * (1 - target_pct),
          stop_price = prev_close * (1 + target_pct)
        This keeps the stop symmetric to the chosen target step.
        """
        record = self.get_symbol_data(symbol)
        if not record:
            return None

        prev_close = record.prev_close

        # fetch target price at requested step
        target_price = self.get_target_by_step(symbol, step_index, side=side)
        if target_price is None:
            return None

        # compute target percentage relative to prev_close
        target_pct = (target_price / prev_close) - 1.0  # could be negative for neg side

        # stop is opposite sign percentage from prev_close
        stop_price = prev_close * (1.0 - target_pct)  # if target_pct positive, this yields below prev_close
        return stop_price
