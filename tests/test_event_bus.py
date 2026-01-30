from core.event_bus import EventBus

def test_event_bus_publish_delivers_to_subscriber():
    bus = EventBus()
    received_payloads = []

    def handler(payload):
        received_payloads.append(payload)

    bus.subscribe("TestEvent", handler)
    bus.publish("TestEvent", {"value": 42})

    assert received_payloads == [{"value": 42}]
