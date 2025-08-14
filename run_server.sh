#!/bin/bash
# Run the MCP server with SSE transport on localhost

# Load port from .env file if it exists
if [ -f .env ]; then
    export $(grep -E '^MCP_SERVER_PORT=' .env | xargs)
fi

# Use port from env or default to 8847
PORT=${MCP_SERVER_PORT:-8847}

echo "🚀 Starting LLM Context Prep MCP Server on localhost:$PORT"
echo "=================================================="
echo ""
echo "To connect Claude Code:"
echo "  claude mcp add --transport sse llm-prep http://localhost:$PORT/sse"
echo ""
echo "Server starting..."
echo ""

# Find Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found! Please install Python 3.8+"
    exit 1
fi

$PYTHON_CMD src/mcp_server_fastmcp.py --transport sse --port $PORT