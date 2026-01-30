from datetime import datetime, timedelta

from core.event_bus import EventBus
from core.logger import Logger
from data.candle_builder import CandleBuilder


def test_candle_builder_basic_flow():
    bus = EventBus()
    logger = Logger("test_candle_builder")

    updates = []
    closed = []

    def on_update(candle):
        updates.append(candle.copy())

    def on_closed(candle):
        closed.append(candle.copy())

    bus.subscribe("CandleUpdateEvent", on_update)
    bus.subscribe("CandleClosedEvent", on_closed)

    builder = CandleBuilder(
        event_bus=bus,
        logger=logger,
        timeframe=timedelta(minutes=1),
    )

    # Tick 1 — opens candle
    bus.publish(
        "TickEvent",
        {
            "symbol": "TEST",
            "price": 100.0,
            "volume": 10,
            "timestamp": datetime(2024, 1, 1, 9, 15, 10),
        },
    )

    # Tick 2 — same minute
    bus.publish(
        "TickEvent",
        {
            "symbol": "TEST",
            "price": 102.0,
            "volume": 5,
            "timestamp": datetime(2024, 1, 1, 9, 15, 40),
        },
    )

    # Tick 3 — next minute → closes previous candle
    bus.publish(
        "TickEvent",
        {
            "symbol": "TEST",
            "price": 101.0,
            "volume": 7,
            "timestamp": datetime(2024, 1, 1, 9, 16, 1),
        },
    )

    # Assertions
    assert len(updates) == 3
    assert len(closed) == 1

    closed_candle = closed[0]

    assert closed_candle["open"] == 100.0
    assert closed_candle["high"] == 102.0
    assert closed_candle["low"] == 100.0
    assert closed_candle["close"] == 102.0
    assert closed_candle["volume"] == 15

    assert closed_candle["start_time"] == datetime(2024, 1, 1, 9, 15)
    assert closed_candle["end_time"] == datetime(2024, 1, 1, 9, 16)
