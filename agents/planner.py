import json
from dataclasses import dataclass, field
from typing import List, Dict, Any
from ..config import CONFIG
from ..kernel.context import Context
from .intent import call_llm

@dataclass
class StateContract:
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)

@dataclass
class TaskNode:
    id: str
    tool: str
    args: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    state_contract: StateContract = field(default_factory=StateContract)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    cost_estimate: float = 0.001
    timeout: int = 30
    retries: int = 1

@dataclass
class TaskDAG:
    nodes: List[TaskNode]
    goal: str

def plan_dag(intent: dict, ctx: Context) -> TaskDAG:
    # Build tool descriptions from schemas
    tool_descs = []
    for name, schema in ctx.tool_schemas.items():
        args_desc = ", ".join([f"{k}: {v['type']}" for k, v in schema["args"].items()])
        tool_descs.append(f"- {name}({args_desc})")
    tools_str = "\n".join(tool_descs)

    sys_prompt = f"""
You are a Planner. Convert the user's intent into a Task DAG (Directed Acyclic Graph).
Available tools:
{tools_str}

Rules:
1. Output a JSON array of nodes.
2. Each node: {{"id": "step1", "tool": "terminal", "args": {{"command": "echo hello"}}, "dependencies": [], "inputs": [], "outputs": [], "state_contract": {{"preconditions": [], "postconditions": []}}, "cost_estimate": 0.001, "timeout": 30, "retries": 1}}
3. Use dependencies to order tasks.
4. Use 'inputs' to list files that must exist before the task.
5. Use 'outputs' to list files that will be created.
6. Keep the DAG small (max {CONFIG['max_dag_nodes']} nodes).
7. Add a state_contract with postconditions like "file_exists:dist/" to verify success.
8. ONLY output the JSON array. No markdown, no explanation.
"""
    user_prompt = f"Intent: {json.dumps(intent)}\nProject Context: {ctx.project}\nCWD: {ctx.cwd}"
    resp = call_llm(
        [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
        CONFIG["planner_model"],
        provider="deepseek",
        is_json=True
    )
    data = json.loads(resp)
    if not isinstance(data, list):
        raise ValueError("Planner did not return a list of nodes.")

    nodes = []
    for item in data:
        sc = StateContract(
            preconditions=item.get("state_contract", {}).get("preconditions", []),
            postconditions=item.get("state_contract", {}).get("postconditions", [])
        )
        node = TaskNode(
            id=item["id"],
            tool=item["tool"],
            args=item.get("args", {}),
            dependencies=item.get("dependencies", []),
            state_contract=sc,
            inputs=item.get("inputs", []),
            outputs=item.get("outputs", []),
            cost_estimate=item.get("cost_estimate", 0.001),
            timeout=item.get("timeout", 30),
            retries=item.get("retries", 1)
        )
        nodes.append(node)
    return TaskDAG(nodes=nodes, goal=intent.get("intent", ""))
