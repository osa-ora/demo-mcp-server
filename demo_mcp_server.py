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


# =========================================================
# DEMO SEARCH
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Search demos by keyword.

The search checks the demo keywords, name and description,
and returns all matching demos together with their available
deployment environments.
"""
)
def find_demo(keyword: str):
    debug(f"Invoke find_demo {keyword}.")
    return helper.find_demo(keyword)


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

Get the full demo definition using its name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def get_demo_details(key: str, environment: str = "local"):
    debug(f"Invoke get_demo_details {key} ({environment}).")
    return helper.fetch_demo_file(key, environment)


# =========================================================
# DEMO PREREQUISITES
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

List the prerequisites required to install and run a demo.

The demo can be identified by name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def get_demo_prerequisites(key: str, environment: str = "local"):
    debug(f"Invoke get_demo_prerequisites {key} ({environment}).")

    demo_def = helper.fetch_demo_file(key, environment)

    prereqs = demo_def.get("prerequisites", [])

    return {
        "demo": demo_def.get("name", key),
        "environment": environment,
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

The demo can be identified by name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def install_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE

    debug(f"Invoke install_demo {key} ({environment}) in {workspace}.")

    return helper.install_demo(
        key=key,
        workspace=workspace,
        environment=environment
    )


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

The demo can be identified by name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def run_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE

    debug(f"Invoke run_demo {key} ({environment}) in {workspace}.")

    return helper.run_demo(
        key=key,
        workspace=workspace,
        environment=environment
    )


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

The demo can be identified by name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def health_check_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE

    debug(f"Invoke health_check_demo {key} ({environment}) in {workspace}.")

    return helper.health_check_demo(
        key=key,
        workspace=workspace,
        environment=environment
    )


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