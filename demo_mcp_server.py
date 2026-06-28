from fastmcp import FastMCP
import asyncio
import mcp_helper as helper
from config import MCP_HOST, MCP_PORT, MCP_TRANSPORT, DEBUG
import os
from typing import Optional

mcp = FastMCP("demo-mcp-server-v1")
DEFAULT_WORKSPACE = "/tmp/mcp-workspace"


# -----------------------------------------------------
# DEBUG HELPER
# -----------------------------------------------------
def debug(msg: str):
    if DEBUG:
        print("DEBUG:" + msg)


# =========================================================
# DEMO REGISTRY
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

List all available demos.
"""
)
def list_demos():
    debug("Invoke list_demos.")
    return helper.fetch_index()


@mcp.tool()
def ping():
    return "ok"

# =========================================================
# DEMO DETAILS
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Get full demo definition and description using its name or ID.
"""
)
def get_demo_details(key: str):
    debug(f"Invoke get_demo {key}.")
    return helper.fetch_demo(key)

# =========================================================
# DEMO PREREQUISITES
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

List the prerequisites required to install and run a specific demo using its name or ID.
"""
)
def get_demo_prerequisites(key: str):
    debug(f"Invoke get_demo_prerequisites {key}.")
    demo_def = helper.fetch_demo(key)
    
    prereqs = demo_def.get("prerequisites", [])
    
    return {
        "demo": demo_def.get("name", key),
        "prerequisites": prereqs if prereqs else ["No prerequisites specified."]
    }

# =========================================================
# DEMO INSTALLATION
# SKILL: demo_registry
# =========================================================

@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Install a demo.

This will:
- validate prerequisites
- clone the demo repository
- create virtual environment
- install dependencies

It takes the demo name or ID and the workspace location where the demo will be installed.
"""
)
def install_demo(key: str, workspace: Optional[str] = None):
    workspace = workspace or DEFAULT_WORKSPACE
    debug(f"Invoke install_demo {key} in {workspace}.")
    return helper.install_demo(key, workspace)


# =========================================================
# DEMO RUN
# SKILL: demo_registry
# =========================================================

@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Run an already installed demo.

This will:
- start the demo application
- validate health endpoint

It takes the demo name or ID and the workspace location where the demo was installed.
"""
)
def run_demo(key: str, workspace: Optional[str] = None):
    workspace = workspace or DEFAULT_WORKSPACE
    debug(f"Invoke run_demo {key} in {workspace}.")
    return helper.run_demo(key, workspace)

# =========================================================
# DEMO HEALTH CHECK
# SKILL: demo_registry
# =========================================================

@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Run only the health check phase of a demo.

This validates that the deployed demo is reachable and healthy.
"""
)
def health_check_demo(key: str, workspace: Optional[str] = None):
    workspace = workspace or DEFAULT_WORKSPACE
    debug(f"Invoke health_check_demo {key} in {workspace}.")
    return helper.health_check_demo(key, workspace)
    
# =========================================================
# MAIN ENTRY
# =========================================================
if __name__ == "__main__":
    print("Debug is set:", DEBUG)

    mcp.run(
        transport=MCP_TRANSPORT,
        host=MCP_HOST,
        port=MCP_PORT
    )
