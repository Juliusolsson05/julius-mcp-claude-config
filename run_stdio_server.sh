#!/bin/bash
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

echo "🚀 Starting LLM Context Prep MCP Server (stdio mode)"
echo "=================================================="
echo ""
echo "This is running in stdio mode for testing."
echo "For Claude Code integration, use run_sse_server.sh instead"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

python src/mcp_server_fastmcp.py --transport stdio
