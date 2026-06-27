import os
from .events import EventBus

class Context:
    """Single source of truth for the kernel."""
    def __init__(self):
        self.cwd = os.getcwd()
        self.tools = {}          # name -> Tool object
        self.tool_schemas = {}   # name -> Schema dict
        self.budget = 0.10
        self.spent = 0.0
        self.state = "IDLE"
        self.execution_log = []
        self.project = self._scan_project()

    def _scan_project(self):
        info = {}
        if os.path.exists("package.json"):
            info["type"] = "node"
        elif os.path.exists("requirements.txt"):
            info["type"] = "python"
        return info
