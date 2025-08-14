#!/bin/bash

# Load port from .env file if it exists
if [ -f .env ]; then
    export $(grep -E '^MCP_SERVER_PORT=' .env | xargs)
fi

# Use port from env or default to 8847
PORT=${MCP_SERVER_PORT:-8847}

echo "=================================================="
echo "📦 Adding LLM Context Prep to Claude Code"
echo "=================================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:$PORT/sse > /dev/null 2>&1; then
    echo "⚠️  Server is not running on port $PORT!"
    echo ""
    echo "Please start the server first:"
    echo "  ./run_sse_server.sh"
    echo ""
    echo "Then run this script again in a new terminal."
    exit 1
fi

echo "✅ Server is running on port $PORT"
echo ""
echo "Adding to Claude Code..."

claude mcp add --transport sse llm-prep http://localhost:$PORT/sse

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully added to Claude Code!"
    echo ""
    echo "Test it by typing /mcp in Claude Code"
else
    echo ""
    echo "❌ Failed to add to Claude Code"
    echo ""
    echo "Make sure you have Claude Code installed and configured"
fi
