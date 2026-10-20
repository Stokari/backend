from common.kernel.bus import EventBus, get_event_bus, set_event_bus


class SampleEvent:
    def __init__(self, value: str):
        self.value = value


class AnotherEvent:
    def __init__(self, count: int):
        self.count = count


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        def handler(event: SampleEvent):
            received.append(event.value)

        bus.subscribe(SampleEvent, handler)
        bus.publish(SampleEvent("hello"))
        assert received == ["hello"]

    def test_multiple_handlers(self):
        bus = EventBus()
        received = []

        def handler1(event: SampleEvent):
            received.append(f"1:{event.value}")

        def handler2(event: SampleEvent):
            received.append(f"2:{event.value}")

        bus.subscribe(SampleEvent, handler1)
        bus.subscribe(SampleEvent, handler2)
        bus.publish(SampleEvent("test"))
        assert received == ["1:test", "2:test"]

    def test_publish_to_wrong_type_no_effect(self):
        bus = EventBus()
        received = []

        def handler(event: SampleEvent):
            received.append(event.value)

        bus.subscribe(SampleEvent, handler)
        bus.publish(AnotherEvent(42))
        assert received == []

    def test_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(event: SampleEvent):
            received.append(event.value)

        bus.subscribe(SampleEvent, handler)
        bus.publish(SampleEvent("first"))
        bus.unsubscribe(SampleEvent, handler)
        bus.publish(SampleEvent("second"))
        assert received == ["first"]

    def test_publish_all(self):
        bus = EventBus()
        received = []

        def handler(event: SampleEvent):
            received.append(event.value)

        bus.subscribe(SampleEvent, handler)
        bus.publish_all([SampleEvent("a"), SampleEvent("b"), SampleEvent("c")])
        assert received == ["a", "b", "c"]

    def test_global_bus(self):
        bus = get_event_bus()
        assert isinstance(bus, EventBus)

    def test_set_global_bus(self):
        original = get_event_bus()
        custom = EventBus()
        set_event_bus(custom)
        try:
            assert get_event_bus() is custom
        finally:
            set_event_bus(original)
