from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

EventHandler = Callable[[Any], None]


@dataclass(slots=True)
class EventBus:
    _handlers: dict[type, list[EventHandler]] = field(default_factory=dict, init=False)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: type, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Any) -> None:
        event_type = type(event)
        for handler in self._handlers.get(event_type, []):
            handler(event)

    def publish_all(self, events: list[Any]) -> None:
        for event in events:
            self.publish(event)


_global_bus: EventBus = EventBus()


def get_event_bus() -> EventBus:
    return _global_bus


def set_event_bus(bus: EventBus) -> None:
    global _global_bus
    _global_bus = bus
