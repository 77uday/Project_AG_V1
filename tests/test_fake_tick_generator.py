from datetime import datetime, timedelta

from core.event_bus import EventBus
from core.clock import ReplayClock
from core.logger import Logger
from data.fake_tick_generator import FakeTickGenerator

def test_fake_tick_emits_event():
    bus = EventBus()
    clock = ReplayClock(datetime(2024, 1, 1, 9, 15))
    logger = Logger("test_tick_logger")

    received = []

    def on_tick(tick):
        received.append(tick)

    bus.subscribe("TickEvent", on_tick)

    gen = FakeTickGenerator(
        symbol="TEST",
        start_price=100.0,
        event_bus=bus,
        clock=clock,
        logger=logger,
        seed=42,
    )

    gen.emit_tick()

    assert len(received) == 1

    tick = received[0]
    assert tick["symbol"] == "TEST"
    assert isinstance(tick["price"], float)
    assert isinstance(tick["volume"], int)
    assert tick["timestamp"] == clock.now()


def test_fake_tick_deterministic_with_seed():
    bus1 = EventBus()
    bus2 = EventBus()

    clock1 = ReplayClock(datetime(2024, 1, 1, 9, 15))
    clock2 = ReplayClock(datetime(2024, 1, 1, 9, 15))

    logger1 = Logger("logger1")
    logger2 = Logger("logger2")

    prices_1 = []
    prices_2 = []

    def on_tick_1(tick):
        prices_1.append(tick["price"])

    def on_tick_2(tick):
        prices_2.append(tick["price"])

    bus1.subscribe("TickEvent", on_tick_1)
    bus2.subscribe("TickEvent", on_tick_2)

    gen1 = FakeTickGenerator(
        symbol="TEST",
        start_price=100.0,
        event_bus=bus1,
        clock=clock1,
        logger=logger1,
        seed=123,
    )

    gen2 = FakeTickGenerator(
        symbol="TEST",
        start_price=100.0,
        event_bus=bus2,
        clock=clock2,
        logger=logger2,
        seed=123,
    )

    gen1.emit_tick()
    gen2.emit_tick()

    assert prices_1 == prices_2
