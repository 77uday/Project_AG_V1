from datetime import datetime, timedelta

from core.clock import RealClock, ReplayClock


def test_real_clock_returns_datetime():
    clock = RealClock()
    now = clock.now()

    assert isinstance(now, datetime)


def test_replay_clock_initial_time():
    start_time = datetime(2024, 1, 1, 9, 15)
    clock = ReplayClock(start_time)

    assert clock.now() == start_time


def test_replay_clock_set_time():
    start_time = datetime(2024, 1, 1, 9, 15)
    new_time = datetime(2024, 1, 1, 9, 30)

    clock = ReplayClock(start_time)
    clock.set(new_time)

    assert clock.now() == new_time


def test_replay_clock_advance_time():
    start_time = datetime(2024, 1, 1, 9, 15)
    clock = ReplayClock(start_time)

    clock.advance(timedelta(minutes=5))

    assert clock.now() == datetime(2024, 1, 1, 9, 20)
