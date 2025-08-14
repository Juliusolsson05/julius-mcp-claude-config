# Makefile for LLM Context Prep MCP Server

.PHONY: help build run test install clean dev docker-build docker-run docker-test

# Default target
help:
	@echo "LLM Context Prep MCP Server - Development Commands"
	@echo "================================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install       Install dependencies locally"
	@echo "  make docker-build  Build Docker image"
	@echo ""
	@echo "Running:"
	@echo "  make run          Run MCP server locally"
	@echo "  make docker-run   Run MCP server in Docker"
	@echo "  make dev          Run in development mode with debug"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run test suite locally"
	@echo "  make docker-test  Run tests in Docker"
	@echo ""
	@echo "Claude Code:"
	@echo "  make claude-add   Add to Claude Code (Docker)"
	@echo "  make claude-local Add to Claude Code (local)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        Clean temporary files"
	@echo "  make format       Format Python code"
	@echo "  make lint         Run linters"

# Installation
install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Docker commands
docker-build:
	docker build -f docker/Dockerfile -t llm-context-prep-mcp:latest .
	@echo "✅ Docker image built: llm-context-prep-mcp:latest"

docker-run:
	docker run -it --rm \
		-v $$(pwd):/workspace \
		-e MCP_DEBUG=$${MCP_DEBUG:-false} \
		llm-context-prep-mcp:latest

docker-test:
	docker run --rm \
		-v $$(pwd):/workspace \
		llm-context-prep-mcp:latest \
		python scripts/test_server.py

# Local running
run:
	python src/mcp_server.py

dev:
	MCP_DEBUG=true python src/mcp_server.py

# Testing
test:
	python scripts/test_server.py

test-coverage:
	pytest --cov=src --cov-report=html scripts/test_server.py
	@echo "✅ Coverage report generated in htmlcov/"

# Claude Code integration
add-command:
	@echo "==============================================="
	@echo "Add MCP Server to Claude Code"
	@echo "==============================================="
	@echo ""
	@echo "Option 1: Connect via localhost (SSE transport) - Port 8847:"
	@echo "------------------------------------------------"
	@echo "1. First, run the server in a terminal:"
	@echo "   python src/mcp_server.py --transport sse --port 8847"
	@echo ""
	@echo "2. Then add to Claude Code:"
	@echo "   claude mcp add --transport sse llm-prep http://localhost:8847/sse"
	@echo ""
	@echo "Option 2: Connect via stdio (local file):"
	@echo "------------------------------------------------"
	@echo "   claude mcp add llm-prep -- python $(shell pwd)/src/mcp_server.py"
	@echo ""
	@echo "Test with: /mcp in Claude Code"
	@echo "=============================================="

claude-add:
	@echo "Adding MCP server to Claude Code (Docker)..."
	claude mcp add llm-prep \
		--env WORKSPACE_DIR='$$(pwd)' \
		-- docker run -i --rm \
		-v '$$(pwd):/workspace' \
		llm-context-prep-mcp:latest
	@echo "✅ Added to Claude Code. Test with: /mcp"

claude-local:
	@echo "Adding MCP server to Claude Code (local)..."
	claude mcp add llm-prep \
		-- python $$(pwd)/src/mcp_server.py
	@echo "✅ Added to Claude Code. Test with: /mcp"

claude-remove:
	claude mcp remove llm-prep
	@echo "✅ Removed from Claude Code"

# Development tools
format:
	@command -v black >/dev/null 2>&1 || pip install black
	black src/ scripts/
	@echo "✅ Code formatted"

lint:
	@command -v ruff >/dev/null 2>&1 || pip install ruff
	ruff check src/ scripts/
	@echo "✅ Linting complete"

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf .ruff_cache/ 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info 2>/dev/null || true
	@echo "✅ Cleaned temporary files"

# Quick start
quickstart:
	@bash scripts/quickstart.sh

# Development environment
dev-setup: install docker-build
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Next steps:"
	@echo "  make test         # Run tests"
	@echo "  make docker-run   # Run in Docker"
	@echo "  make claude-add   # Add to Claude Code"

# Release
release: clean format lint test docker-build
	@echo "✅ Ready for release"
	@echo ""
	@echo "Don't forget to:"
	@echo "  1. Update version in README.md"
	@echo "  2. Tag the release: git tag v1.0.0"
	@echo "  3. Push to registry: docker push ..."




# Prints the full STDIO command for Claude Code, then asks to copy it
claude-stdio-cmd:
	@BASE=$$(pwd -P); \
	if [ -x venv/bin/python ]; then PY="$$BASE/venv/bin/python"; \
	elif command -v python3 >/dev/null 2>&1; then PY=$$(command -v python3); \
	else PY=$$(command -v python); fi; \
	SCRIPT="$$BASE/src/mcp_server_fastmcp.py"; \
	CMD="claude mcp add llm-prep -- \"$$PY\" \"$$SCRIPT\" --transport stdio"; \
	echo "$$CMD"; \
	printf "Copy to clipboard? [y/N] "; \
	read ans; \
	case "$$ans" in \
	  y|Y) \
	    if command -v pbcopy >/dev/null 2>&1; then printf "%s" "$$CMD" | pbcopy && echo "✅ Copied to clipboard (pbcopy)."; \
	    elif command -v xclip >/dev/null 2>&1; then printf "%s" "$$CMD" | xclip -selection clipboard && echo "✅ Copied to clipboard (xclip)."; \
	    elif command -v wl-copy >/dev/null 2>&1; then printf "%s" "$$CMD" | wl-copy && echo "✅ Copied to clipboard (wl-copy)."; \
	    else echo "⚠️  No clipboard tool found (pbcopy/xclip/wl-copy)."; fi ;; \
	  *) echo "Skipped copying."; ;; \
	esac





# Show current configuration
config:
	@echo "Current Configuration:"
	@echo "====================="
	@echo "MCP_DEBUG: $${MCP_DEBUG:-false}"
	@echo "MCP_MAX_FILE_SIZE: $${MCP_MAX_FILE_SIZE:-10485760}"
	@echo "MCP_MAX_CONTEXT_SIZE: $${MCP_MAX_CONTEXT_SIZE:-52428800}"
	@echo "WORKSPACE: $$(pwd)"
