from strategy.intent_events import IntentEvent, TriggerSpec, Side

def side_to_store_side(side: Side) -> str:
    return "pos" if side == Side.LONG else "neg"
