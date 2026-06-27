class EventBus:
    """Simple event bus for decoupled communication."""
    def __init__(self):
        self._subs = {}

    def subscribe(self, event_type, callback):
        self._subs.setdefault(event_type, []).append(callback)

    def emit(self, event_type, data=None):
        for cb in self._subs.get(event_type, []):
            cb(data)
