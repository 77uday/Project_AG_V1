# ============================================================
# IMPORTS
# ============================================================

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Any, Dict


# ============================================================
# DATA MODELS: Intent & Trigger
# ============================================================

class Side(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class TriggerSpec:
    """
    A single conditional trigger inside an Intent.

    - side: LONG or SHORT (explicit; do NOT use signed indices).
    - step_index: positive 1-based integer selecting the nth precomputed level.
    - timeout_seconds: how long OrderManager will wait for the flip after target is reached.
    - valid_until: optional datetime to expire this trigger early.
    - priority: ordering among triggers (lower => higher priority).
    - meta: free-form map for strategy notes / debugging.
    """
    side: Side
    step_index: int
    timeout_seconds: int = 60
    valid_until: Optional[datetime] = None
    priority: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentEvent:
    """
    Strategy -> Risk -> Execution intention.

    - intent_id: unique id (strategy should set)
    - strategy_id: id/name of strategy
    - symbol: symbol this intent targets
    - triggers: list of TriggerSpec (usually both LONG and SHORT for same step_index)
    - auto_advance: if strategy wants to auto-advance after fills (pattern B)
    - created_at: timestamp
    - correlation_id: useful to link multiple intents in a workflow
    - session_date: session identification
    """
    intent_id: str
    strategy_id: str
    symbol: str
    triggers: List[TriggerSpec]
    auto_advance: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    session_date: Optional[str] = None


# ============================================================
# APPROVAL / LIFECYCLE EVENTS
# ============================================================

@dataclass
class ApprovedIntentEvent:
    intent: IntentEvent
    approved_by: str
    approved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RejectedIntentEvent:
    intent: IntentEvent
    reason: str
    rejected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class IntentExpiredEvent:
    intent: IntentEvent
    reason: Optional[str]
    expired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
