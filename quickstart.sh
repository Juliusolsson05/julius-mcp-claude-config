#!/bin/bash

# Quick Start Script for LLM Context Prep MCP Server
# Automatically detects environment and sets up everything

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "🚀 LLM Context Prep MCP Server - Quick Start"
echo "==========================================="
echo ""

# Check what's available
HAS_DOCKER=false
HAS_PYTHON=false

if command -v docker &> /dev/null; then
    HAS_DOCKER=true
    echo -e "${GREEN}✅ Docker found${NC}"
fi

if command -v python3 &> /dev/null || command -v python &> /dev/null; then
    HAS_PYTHON=true
    echo -e "${GREEN}✅ Python found${NC}"
fi

echo ""

# If neither is available, show installation instructions
if [ "$HAS_DOCKER" = false ] && [ "$HAS_PYTHON" = false ]; then
    echo -e "${RED}❌ Neither Docker nor Python found!${NC}"
    echo ""
    echo "Please install one of the following:"
    echo "  • Python 3.8+: https://www.python.org"
    echo "  • Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Prefer local Python setup for simplicity
if [ "$HAS_PYTHON" = true ]; then
    echo -e "${BLUE}Using Python setup (recommended for localhost connection)${NC}"
    echo ""
    
    # Check if get_started.sh exists
    if [ -f "get_started.sh" ]; then
        echo "Running automated setup..."
        ./get_started.sh
    else
        echo -e "${YELLOW}get_started.sh not found, running basic setup...${NC}"
        
        # Basic Python setup
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        else
            PYTHON_CMD="python"
        fi
        
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
        
        echo "Installing dependencies..."
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
            venv/Scripts/pip install -r requirements.txt
        else
            venv/bin/pip install -r requirements.txt
        fi
        
        echo ""
        echo -e "${GREEN}✅ Setup complete!${NC}"
        echo ""
        echo "To start the server:"
        echo "  1. Run: ./run_server.sh"
        echo "  2. In another terminal: claude mcp add --transport sse llm-prep http://localhost:8847/sse"
    fi
    
elif [ "$HAS_DOCKER" = true ]; then
    echo -e "${BLUE}Using Docker setup${NC}"
    echo ""
    
    # Docker setup
    echo "📦 Setting up Docker image..."
    if docker pull llm-context-prep-mcp:latest 2>/dev/null; then
        echo "✅ Image downloaded"
    else
        echo "Building image locally (this may take a minute)..."
        docker build -f docker/Dockerfile -t llm-context-prep-mcp:latest .
        echo "✅ Image built"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Docker setup complete!${NC}"
    echo ""
    echo "To use with Claude Code:"
    echo -e "${YELLOW}claude mcp add llm-prep -- docker run -i --rm -v '\$(pwd):/workspace' llm-context-prep-mcp:latest${NC}"
    echo ""
    echo "To test the server:"
    echo -e "${YELLOW}docker run --rm llm-context-prep-mcp:latest python scripts/test_server.py${NC}"
fi

echo ""
echo "==========================================="
echo "📚 For more options, see README.md"
echo "❓ Need help? Run: make help"
echo "==========================================="