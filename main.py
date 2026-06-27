#!/usr/bin/env python3
"""
Atlas Kernel – Action Compiler OS
Entry point for the CLI.
"""

import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import kernel components
from .config import CONFIG
from .kernel.events import EventBus
from .kernel.context import Context
from .kernel.memory import Memory
from .kernel.state import StateMachine
from .kernel.resource import ResourceManager
from .kernel.snapshot import SnapshotManager

# Import agents
from .agents.intent import compile_intent
from .agents.planner import plan_dag, TaskDAG, TaskNode, StateContract
from .agents.reflector import reflect

# Import tools
from .tools.builtin import init_tools

# ============================================================
# DAG COMPILER (Validation)
# ============================================================
def validate_dag(dag: TaskDAG) -> tuple:
    # Cycle detection (DFS)
    graph = {n.id: set(n.dependencies) for n in dag.nodes}
    visited = set()
    stack = set()
    def dfs(node):
        if node in stack:
            return False
        if node in visited:
            return True
        stack.add(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                return False, f"Dependency '{dep}' missing"
            if not dfs(dep):
                return False, f"Cycle involving {node}"
        stack.remove(node)
        visited.add(node)
        return True
    for n in dag.nodes:
        if n.id not in visited:
            if not dfs(n.id):
                return False, "Cycle detected"
    # Max nodes
    if len(dag.nodes) > CONFIG["max_dag_nodes"]:
        return False, f"DAG too large ({len(dag.nodes)} > {CONFIG['max_dag_nodes']})"
    # Check tool schemas
    from .tools.builtin import TOOL_SCHEMAS
    for n in dag.nodes:
        if n.tool not in TOOL_SCHEMAS:
            return False, f"Unknown tool '{n.tool}'"
        schema = TOOL_SCHEMAS[n.tool]
        for arg, spec in schema["args"].items():
            if spec.get("required", False) and arg not in n.args:
                return False, f"Node {n.id} missing required arg '{arg}'"
    return True, "Valid DAG"

# ============================================================
# SIMULATOR (Static Analysis)
# ============================================================
def simulate(dag: TaskDAG, ctx: Context) -> tuple:
    # Check preconditions (file existence)
    for n in dag.nodes:
        for pre in n.state_contract.preconditions:
            if pre.startswith("file_exists:"):
                filepath = pre.replace("file_exists:", "")
                if not os.path.exists(os.path.join(ctx.cwd, filepath)):
                    return False, f"Precondition failed for {n.id}: {filepath} missing"
        for inp in n.inputs:
            if not os.path.exists(os.path.join(ctx.cwd, inp)):
                return False, f"Input file missing for {n.id}: {inp}"
    # Budget
    total_cost = sum(n.cost_estimate for n in dag.nodes)
    if total_cost + ctx.spent > ctx.budget:
        return False, f"Budget exceeded: ${total_cost + ctx.spent:.3f} > ${ctx.budget:.3f}"
    return True, "Simulation passed"

# ============================================================
# EXECUTOR (Parallel DAG Runner)
# ============================================================
def execute_dag(dag: TaskDAG, ctx: Context, bus: EventBus) -> dict:
    node_map = {n.id: n for n in dag.nodes}
    indegree = {n.id: len(n.dependencies) for n in dag.nodes}
    ready = [n.id for n in dag.nodes if indegree[n.id] == 0]
    results = {}
    completed = set()
    executor = ThreadPoolExecutor(max_workers=4)

    def run_node(node_id):
        node = node_map[node_id]
        bus.emit("node_started", {"id": node_id, "tool": node.tool})
        tool_obj = ctx.tools[node.tool]
        for attempt in range(node.retries + 1):
            try:
                output = tool_obj.func(ctx, **node.args)
                results[node_id] = {"status": "success", "output": output, "attempts": attempt+1}
                ctx.spent += node.cost_estimate
                bus.emit("node_finished", {"id": node_id, "result": results[node_id]})
                return results[node_id]
            except Exception as e:
                if attempt < node.retries:
                    time.sleep(1)
                    continue
                results[node_id] = {"status": "failed", "error": str(e), "attempts": attempt+1}
                bus.emit("node_failed", {"id": node_id, "error": str(e)})
                return results[node_id]

    with executor:
        futures = {}
        while ready:
            # Submit all currently ready nodes
            for node_id in ready:
                if node_id not in futures:
                    futures[node_id] = executor.submit(run_node, node_id)
            # Wait for at least one to finish
            done_futures = [f for f in futures.values() if f.done()]
            for fut in done_futures:
                # identify which node finished
                for nid, f in list(futures.items()):
                    if f == fut:
                        result = f.result()
                        completed.add(nid)
                        if result["status"] == "failed":
                            # Fail-fast: stop all future submissions
                            return results
                        # Update indegrees
                        for n in dag.nodes:
                            if nid in n.dependencies:
                                indegree[n.id] -= 1
                                if indegree[n.id] == 0:
                                    ready.append(n.id)
                        # Remove from futures
                        del futures[nid]
                        break
            # Refresh ready list (remove already completed)
            ready = [r for r in ready if r not in completed and r not in futures]
            # If no futures left and ready is empty, we're done
            if not futures and not ready:
                break
            # Avoid busy loop
            time.sleep(0.1)
    return results

# ============================================================
# VERIFIER (Postconditions)
# ============================================================
def verify(dag: TaskDAG, results: dict, ctx: Context) -> tuple:
    all_success = all(r["status"] == "success" for r in results.values())
    if not all_success:
        return False, "Some nodes failed."
    for n in dag.nodes:
        if n.id not in results or results[n.id]["status"] != "success":
            continue
        for post in n.state_contract.postconditions:
            if post.startswith("file_exists:"):
                filepath = post.replace("file_exists:", "")
                if not os.path.exists(os.path.join(ctx.cwd, filepath)):
                    return False, f"Postcondition failed for {n.id}: {filepath} not created."
            if post.startswith("dir_exists:"):
                dirpath = post.replace("dir_exists:", "")
                if not os.path.isdir(os.path.join(ctx.cwd, dirpath)):
                    return False, f"Postcondition failed for {n.id}: {dirpath} not created."
    return True, "Verification passed."

# ============================================================
# MAIN ORCHESTRATOR
# ============================================================
def main():
    bus = EventBus()
    ctx = Context()
    init_tools(ctx)
    memory = Memory(CONFIG["memory_db"])
    state = StateMachine(ctx, bus)

    # Subscribe to events for logging
    bus.subscribe("node_started", lambda d: print(f"  ▶ {d['id']} ({d['tool']})"))
    bus.subscribe("node_finished", lambda d: print(f"    ✔ {d['id']} done"))
    bus.subscribe("node_failed", lambda d: print(f"    ❌ {d['id']} failed: {d.get('error', '')}"))

    print("\n" + "="*60)
    print("🖥️  Atlas Kernel v2 (Action Compiler OS)")
    print("   CWD:", ctx.cwd)
    print("   Budget: $", ctx.budget)
    print("   Project:", ctx.project)
    print("   Type 'exit' to quit.")
    print("="*60 + "\n")

    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        # ---- Step 1: Intent Compiler (Fast Groq) ----
        print("[1/7] Compiling intent...")
        intent = compile_intent(user_input)
        print(f"    Intent: {intent.get('intent')}")
        print(f"    Constraints: {intent.get('constraints')}")

        # ---- Step 2: Planner (Creative Layer) ----
        print("[2/7] Planning DAG (DeepSeek)...")
        try:
            dag = plan_dag(intent, ctx)
            print(f"    Generated {len(dag.nodes)} nodes.")
        except Exception as e:
            print(f"❌ Planner failed: {e}")
            continue

        # ---- Step 3: DAG Compiler (Validation) ----
        print("[3/7] Compiling DAG...")
        valid, msg = validate_dag(dag)
        if not valid:
            print(f"❌ DAG invalid: {msg}")
            continue
        print("    ✅ DAG valid.")

        # ---- Step 4: Simulator (Static Analysis) ----
        print("[4/7] Simulating...")
        sim_ok, sim_msg = simulate(dag, ctx)
        if not sim_ok:
            print(f"❌ Simulation failed: {sim_msg}")
            continue
        print("    ✅ Simulation passed.")

        # ---- Step 5: Executor ----
        print("[5/7] Executing...")
        results = execute_dag(dag, ctx, bus)

        # ---- Step 6: Verifier ----
        print("[6/7] Verifying...")
        verified, verify_msg = verify(dag, results, ctx)
        if verified:
            print("    ✅ Verification passed.")
        else:
            print(f"    ❌ Verification failed: {verify_msg}")

        # ---- Step 7: Reflector (Async) ----
        print("[7/7] Reflecting...")
        reflect(dag, verified, memory, ctx)

        # ---- Summary ----
        print("\n📊 Summary:")
        for node_id, res in results.items():
            status = res['status']
            icon = "✅" if status == "success" else "❌"
            print(f"  {icon} {node_id}: {status} (attempts: {res.get('attempts', 0)})")
        print(f"💰 Cost: ${ctx.spent:.4f}")
        print()

if __name__ == "__main__":
    main()
