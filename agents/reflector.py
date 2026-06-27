import json
import hashlib
import os
from ..config import CONFIG
from ..kernel.memory import Memory
from .intent import call_llm

def reflect(dag, success, memory: Memory, context):
    """Async – stores procedural memory on success."""
    if not success:
        return
    # Fingerprint the goal
    goal_hash = hashlib.md5(dag.goal.encode()).hexdigest()
    memory.store(
        mem_type="procedural",
        key=f"workflow:{goal_hash}",
        value=json.dumps([{"id": n.id, "tool": n.tool, "args": n.args, "deps": n.dependencies} for n in dag.nodes]),
        source_type="llm",
        scope=f"project:{os.getcwd()}",
        metadata={"goal": dag.goal, "nodes": len(dag.nodes)}
    )
    print("[Reflector] Stored workflow in procedural memory.")
