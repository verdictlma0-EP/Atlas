from .events import EventBus

class StateMachine:
    def __init__(self, context, bus):
        self.ctx = context
        self.bus = bus

    def transition(self, new_state, data=None):
        old = self.ctx.state
        self.ctx.state = new_state
        self.bus.emit("state_changed", {"from": old, "to": new_state, "data": data})
