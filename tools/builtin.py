import os
import subprocess
from .registry import Tool

# Schema definitions (OpenAPI‑style)
TOOL_SCHEMAS = {
    "terminal": {
        "args": {"command": {"type": "string", "required": True}},
        "preconditions": [],
        "postconditions": []
    },
    "write_file": {
        "args": {"path": {"type": "string", "required": True}, "content": {"type": "string", "required": True}},
        "preconditions": [],
        "postconditions": ["file_exists:{path}"]
    },
    "read_file": {
        "args": {"path": {"type": "string", "required": True}},
        "preconditions": ["file_exists:{path}"],
        "postconditions": []
    },
}

def terminal_tool(ctx, command):
    result = subprocess.run(command, shell=True, cwd=ctx.cwd, capture_output=True, text=True, timeout=30)
    return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}

def write_file_tool(ctx, path, content):
    full_path = os.path.join(ctx.cwd, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"status": "written", "path": path}

def read_file_tool(ctx, path):
    with open(os.path.join(ctx.cwd, path), 'r', encoding='utf-8') as f:
        return {"content": f.read()}

def init_tools(ctx):
    ctx.tools["terminal"] = Tool("terminal", terminal_tool, TOOL_SCHEMAS["terminal"])
    ctx.tools["write_file"] = Tool("write_file", write_file_tool, TOOL_SCHEMAS["write_file"])
    ctx.tools["read_file"] = Tool("read_file", read_file_tool, TOOL_SCHEMAS["read_file"])
    ctx.tool_schemas = TOOL_SCHEMAS
