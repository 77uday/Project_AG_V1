from datetime import datetime

from core.event_bus import EventBus
from core.clock import ReplayClock
from core.logger import Logger
from data.replay_loader import ReplayLoader

def test_replay_loader_emits_ticks_in_order():
    # Recorded tick data (as iterator)
    recorded_ticks = iter([
        {
            "symbol": "TEST",
            "price": 100.0,
            "volume": 10,
            "timestamp": datetime(2024, 1, 1, 9, 15),
        },
        {
            "symbol": "TEST",
            "price": 101.0,
            "volume": 20,
            "timestamp": datetime(2024, 1, 1, 9, 16),
        },
    ])

    bus = EventBus()
    clock = ReplayClock(datetime(2024, 1, 1, 9, 0))
    logger = Logger("test_replay_logger")

    received = []

    def on_tick(tick):
        received.append((tick["price"], clock.now()))

    bus.subscribe("TickEvent", on_tick)

    replay = ReplayLoader(
        ticks=recorded_ticks,
        event_bus=bus,
        clock=clock,
        logger=logger,
    )


    # Replay first tick
    assert replay.replay_next() is True
    # Replay second tick
    assert replay.replay_next() is True
    # Replay finished
    assert replay.replay_next() is False


    # Verify order and timestamps
    assert received == [
        (100.0, datetime(2024, 1, 1, 9, 15)),
        (101.0, datetime(2024, 1, 1, 9, 16)),
    ]
