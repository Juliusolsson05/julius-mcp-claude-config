#!/bin/bash
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Load port from .env file if it exists
if [ -f .env ]; then
    export $(grep -E '^MCP_SERVER_PORT=' .env | xargs)
fi

# Use port from env or default to 8847
PORT=${MCP_SERVER_PORT:-8847}

echo "🚀 Starting LLM Context Prep MCP Server on localhost:$PORT"
echo "=================================================="
echo ""
echo "Server is running at: http://localhost:$PORT/sse"
echo ""
echo "To connect Claude Code, run in another terminal:"
echo "  claude mcp add --transport sse llm-prep http://localhost:$PORT/sse"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================================="
echo ""

python src/mcp_server_fastmcp.py --transport sse --port $PORT
