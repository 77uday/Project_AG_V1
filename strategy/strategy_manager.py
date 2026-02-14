# ============================================================
# IMPORTS
# ============================================================

from core.derived_data.derived_data_store import DerivedDataStore
from core.logger import Logger
from core.event_bus import EventBus

# import factory from dummy strategy
from strategy.dummy_strategy import create_dummy_strategy

# ============================================================
# FACTORY WRAPPER
# ============================================================

def create_strategy(event_bus: EventBus, logger: Logger, store: DerivedDataStore, strategy_id: str = "DUMMY"):
    """
    Project-level entrypoint to create the strategy instance.
    Keeps integration points in one place.
    """
    return create_dummy_strategy(event_bus=event_bus, logger=logger, store=store, strategy_id=strategy_id)
