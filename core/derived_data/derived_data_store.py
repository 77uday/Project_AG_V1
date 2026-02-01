# ============================================================
# IMPORTS
# ============================================================

from abc import ABC, abstractmethod
from typing import Any


# ============================================================
# DERIVED DATA STORE (INTERFACE)
# ============================================================

class DerivedDataStore(ABC):

    @abstractmethod
    def persist_universe_snapshot(self, snapshot: Any) -> None:
        pass

    @abstractmethod
    def persist_derived_symbol_data(self, data: Any) -> None:
        pass

    @abstractmethod
    def persist_gap_snapshot(self, snapshot: Any) -> None:
        pass
