#!/bin/bash

# Quick Start Script for LLM Context Prep MCP Server
# Run this to get started in under 30 seconds!

set -e

echo "🚀 LLM Context Prep MCP Server - Quick Start"
echo "==========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker compose is available
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif docker-compose version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Docker Compose is not installed!"
    echo "Please install Docker Compose"
    exit 1
fi

echo "✅ Docker found"
echo ""

# Pull or build the image
echo "📦 Setting up Docker image..."
if docker pull llm-context-prep-mcp:latest 2>/dev/null; then
    echo "✅ Image downloaded"
else
    echo "Building image locally (this may take a minute)..."
    docker build -f docker/Dockerfile -t llm-context-prep-mcp:latest .
    echo "✅ Image built"
fi

echo ""
echo "🎯 Quick Start Options:"
echo "======================"
echo ""
echo "1. Test the server:"
echo "   docker run --rm llm-context-prep-mcp:latest python src/test_server.py"
echo ""
echo "2. Run with current directory:"
echo "   docker run -it --rm -v \$(pwd):/workspace llm-context-prep-mcp:latest"
echo ""
echo "3. Add to Claude Code:"
echo "   claude mcp add llm-prep -- docker run -i --rm -v '\$(pwd):/workspace' llm-context-prep-mcp:latest"
echo ""
echo "4. Use docker-compose:"
echo "   $COMPOSE_CMD -f docker/docker-compose.yml up"
echo ""
echo "📚 Documentation: README.md"
echo "🧪 Run tests: docker run --rm llm-context-prep-mcp:latest python scripts/test_server.py"
echo ""
echo "✨ Ready to use! Choose an option above to get started."
