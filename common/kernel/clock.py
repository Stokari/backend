from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...

    @abstractmethod
    def now_utc(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class FixedClock(Clock):
    fixed_time: datetime

    def now(self) -> datetime:
        return self.fixed_time

    def now_utc(self) -> datetime:
        return self.fixed_time


_default_clock: Clock = SystemClock()


def get_clock() -> Clock:
    return _default_clock


def set_clock(clock: Clock) -> None:
    global _default_clock
    _default_clock = clock
