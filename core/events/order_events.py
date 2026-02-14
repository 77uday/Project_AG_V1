# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# ============================================================
# ORDER EVENTS (minimal)
# ============================================================

@dataclass
class OrderFillEvent:
    intent_id: Optional[str]
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    qty: Optional[float] = None
    price: Optional[float] = None
    timestamp: datetime = datetime.now(timezone.utc)
