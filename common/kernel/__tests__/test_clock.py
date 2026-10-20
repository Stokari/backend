from datetime import datetime, timedelta, timezone

from common.kernel.clock import Clock, FixedClock, SystemClock, get_clock, set_clock


class TestSystemClock:
    def test_now_returns_utc(self):
        clock = SystemClock()
        now = clock.now()
        assert now.tzinfo == timezone.utc

    def test_now_utc_returns_utc(self):
        clock = SystemClock()
        now = clock.now_utc()
        assert now.tzinfo == timezone.utc

    def test_now_is_recent(self):
        clock = SystemClock()
        now = clock.now()
        diff = datetime.now(timezone.utc) - now
        assert diff < timedelta(seconds=1)


class TestFixedClock:
    def test_fixed_clock_returns_fixed_time(self):
        fixed = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed)
        assert clock.now() == fixed
        assert clock.now_utc() == fixed

    def test_fixed_clock_multiple_calls_same(self):
        fixed = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock = FixedClock(fixed)
        assert clock.now() == clock.now() == clock.now_utc()


class TestGlobalClock:
    def test_default_is_system_clock(self):
        clock = get_clock()
        assert isinstance(clock, SystemClock)

    def test_can_override_clock(self):
        fixed = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        custom = FixedClock(fixed)
        set_clock(custom)
        try:
            assert get_clock() is custom
            assert get_clock().now() == fixed
        finally:
            set_clock(SystemClock())

    def test_clock_protocol(self):
        assert issubclass(SystemClock, Clock)
        assert issubclass(FixedClock, Clock)
