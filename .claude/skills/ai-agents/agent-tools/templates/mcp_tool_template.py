#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Tool Template.

Template for creating tools that integrate with MCP servers.
MCP tools allow agents to interact with external services
through a standardized protocol.

See: https://modelcontextprotocol.io/
"""

from typing import Optional, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# MCP Tool Input/Output Schemas
# ============================================================================

class MCPToolInput(BaseModel):
    """Standard input schema for MCP tools."""
    action: str = Field(description="The action to perform")
    params: dict = Field(default_factory=dict, description="Action parameters")
    context: Optional[dict] = Field(default=None, description="Optional context")


class MCPToolOutput(BaseModel):
    """Standard output schema for MCP tools."""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Optional[dict] = None


# ============================================================================
# MCP Client Wrapper
# ============================================================================

class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url
        self.api_key = api_key

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server."""
        import httpx

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/tools/{tool_name}",
                json={"arguments": arguments},
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return {"success": True, "result": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

    async def list_tools(self) -> list[dict]:
        """List available tools on the MCP server."""
        import httpx

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.server_url}/tools",
                headers=headers,
                timeout=10
            )
            return response.json() if response.status_code == 200 else []


# ============================================================================
# MCP Tool Factory
# ============================================================================

def create_mcp_tool(
    name: str,
    description: str,
    mcp_server_url: str,
    mcp_tool_name: str,
    api_key: Optional[str] = None
):
    """Factory function to create an MCP-connected tool.

    Args:
        name: Name for the LangChain tool
        description: Description for the LLM
        mcp_server_url: URL of the MCP server
        mcp_tool_name: Name of the tool on the MCP server
        api_key: Optional API key for authentication

    Returns:
        A LangChain tool that calls the MCP server
    """

    @tool(name=name)
    async def mcp_tool(params: dict) -> dict:
        """Call the MCP server tool."""
        client = MCPClient(mcp_server_url, api_key)
        result = await client.call_tool(mcp_tool_name, params)
        return result

    # Update docstring
    mcp_tool.__doc__ = f"""{description}

    This tool connects to an MCP server to perform the action.

    Args:
        params: Dictionary of parameters for the MCP tool

    Returns:
        Result from the MCP server
    """

    return mcp_tool


# ============================================================================
# Example MCP Tools
# ============================================================================

# Example: Database MCP Tool
@tool
async def mcp_database_query(
    query: str,
    database: str = "default"
) -> dict:
    """Execute a database query via MCP server.

    Use this tool when you need to query a database through
    the MCP database server.

    Args:
        query: SQL query to execute
        database: Database name (default: "default")

    Returns:
        Query results from the database
    """
    import os

    server_url = os.environ.get("MCP_DATABASE_URL", "http://localhost:3000")
    api_key = os.environ.get("MCP_DATABASE_KEY")

    client = MCPClient(server_url, api_key)
    result = await client.call_tool("query", {
        "sql": query,
        "database": database
    })

    return result


# Example: File System MCP Tool
@tool
async def mcp_file_read(
    path: str,
    encoding: str = "utf-8"
) -> dict:
    """Read a file via MCP file system server.

    Use this tool when you need to read files through
    the MCP file system server (sandboxed access).

    Args:
        path: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        File contents
    """
    import os

    server_url = os.environ.get("MCP_FILESYSTEM_URL", "http://localhost:3001")
    api_key = os.environ.get("MCP_FILESYSTEM_KEY")

    client = MCPClient(server_url, api_key)
    result = await client.call_tool("read_file", {
        "path": path,
        "encoding": encoding
    })

    return result


# Example: Search MCP Tool
@tool
async def mcp_web_search(
    query: str,
    num_results: int = 5
) -> dict:
    """Search the web via MCP search server.

    Use this tool when you need to search the web through
    the MCP search server.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        Search results
    """
    import os

    server_url = os.environ.get("MCP_SEARCH_URL", "http://localhost:3002")
    api_key = os.environ.get("MCP_SEARCH_KEY")

    client = MCPClient(server_url, api_key)
    result = await client.call_tool("search", {
        "query": query,
        "limit": num_results
    })

    return result


# ============================================================================
# MCP Tool Registry
# ============================================================================

class MCPToolRegistry:
    """Registry for managing MCP tools."""

    def __init__(self):
        self.tools = {}
        self.clients = {}

    def register_server(self, name: str, url: str, api_key: Optional[str] = None):
        """Register an MCP server."""
        self.clients[name] = MCPClient(url, api_key)

    def create_tool(self, server_name: str, tool_name: str, description: str):
        """Create a tool from a registered server."""
        if server_name not in self.clients:
            raise ValueError(f"Server {server_name} not registered")

        client = self.clients[server_name]

        @tool(name=f"{server_name}_{tool_name}")
        async def mcp_tool(params: dict) -> dict:
            return await client.call_tool(tool_name, params)

        mcp_tool.__doc__ = description
        self.tools[f"{server_name}_{tool_name}"] = mcp_tool
        return mcp_tool

    def get_all_tools(self) -> list:
        """Get all registered tools."""
        return list(self.tools.values())


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def main():
        # Create MCP tool using factory
        db_tool = create_mcp_tool(
            name="database_query",
            description="Query the database",
            mcp_server_url="http://localhost:3000",
            mcp_tool_name="query"
        )

        print(f"Created tool: {db_tool.name}")

        # Using registry
        registry = MCPToolRegistry()
        registry.register_server("db", "http://localhost:3000", "api_key")
        registry.register_server("files", "http://localhost:3001")

        # Create tools from registry
        query_tool = registry.create_tool(
            "db", "query", "Execute database queries"
        )
        read_tool = registry.create_tool(
            "files", "read", "Read files from filesystem"
        )

        print(f"Registry tools: {[t.name for t in registry.get_all_tools()]}")

    asyncio.run(main())
