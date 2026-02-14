# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime

from strategy.intent_events import (
    IntentEvent,
    TriggerSpec,
    Side,
    ApprovedIntentEvent,
    RejectedIntentEvent,
    IntentExpiredEvent,
)


# ============================================================
# TEST: TriggerSpec construction
# ============================================================

def test_trigger_spec_creation():
    trigger = TriggerSpec(
        side=Side.LONG,
        step_index=1,
        timeout_seconds=60,
    )

    assert trigger.side == Side.LONG
    assert trigger.step_index == 1
    assert trigger.timeout_seconds == 60


# ============================================================
# TEST: IntentEvent construction with triggers
# ============================================================

def test_intent_event_creation():
    triggers = [
        TriggerSpec(side=Side.LONG, step_index=1),
        TriggerSpec(side=Side.SHORT, step_index=1),
    ]

    intent = IntentEvent(
        intent_id="TEST-1",
        strategy_id="DUMMY",
        symbol="AAA",
        triggers=triggers,
        auto_advance=True,
        created_at=datetime.utcnow(),
        correlation_id="CORR-1",
        session_date="2026-02-14",
    )

    assert intent.intent_id == "TEST-1"
    assert intent.strategy_id == "DUMMY"
    assert intent.symbol == "AAA"
    assert len(intent.triggers) == 2
    assert intent.triggers[0].side == Side.LONG
    assert intent.triggers[1].side == Side.SHORT
    assert intent.auto_advance is True


# ============================================================
# TEST: Approval & lifecycle events
# ============================================================

def test_intent_lifecycle_events():
    trigger = TriggerSpec(side=Side.LONG, step_index=1)

    intent = IntentEvent(
        intent_id="TEST-2",
        strategy_id="DUMMY",
        symbol="BBB",
        triggers=[trigger],
        auto_advance=True,
        created_at=datetime.utcnow(),
    )

    approved = ApprovedIntentEvent(intent=intent, approved_by="RiskManager")
    rejected = RejectedIntentEvent(intent=intent, reason="Capital limit")
    expired = IntentExpiredEvent(intent=intent, reason="Timeout")

    assert approved.intent.intent_id == "TEST-2"
    assert rejected.reason == "Capital limit"
    assert expired.reason == "Timeout"
