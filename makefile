# -------- Config --------
PY ?= venv/bin/python
PIP ?= venv/bin/pip

# -------- Help --------
.PHONY: help
help:
	@echo ""
	@echo "Julius MCP Collection – Commands"
	@echo "================================="
	@echo ""
	@echo "🚀 QUICK START:"
	@echo "  make setup           → Set up everything (all servers + dependencies)"
	@echo "  make install-cmd     → Get the Claude install command (copies to clipboard)"
	@echo ""
	@echo "📦 Individual Commands:"
	@echo "  make install-llm     → Get install command for llm-prep only"
	@echo "  make config          → Generate claude_desktop_config.json content"
	@echo "  make list            → List all managed MCP servers"
	@echo ""
	@echo "🛠️  Development:"
	@echo "  make test            → Run tests"
	@echo "  make lint            → Run linter"
	@echo "  make fmt             → Format code"
	@echo "  make doctor          → Check environment"
	@echo "  make clean           → Clean caches"
	@echo "  make reset           → Full reset (remove all venvs)"
	@echo ""

# -------- Main Setup --------
.PHONY: setup
setup:
	@echo "🚀 Setting up Julius MCP Collection..."
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 [1/4] Initializing git submodules..."
	@git submodule update --init --recursive
	@echo "🐍 [2/4] Setting up llm-prep server..."
	@if [ ! -d venv ]; then python3 -m venv venv; fi
	@$(PIP) install --upgrade pip >/dev/null
	@$(PIP) install -r requirements.txt >/dev/null
	@echo "🔍 [3/4] Setting up DuckDuckGo search server..."
	@cd submodules/duckduckgo-mcp-server && \
		if [ ! -d venv ]; then python3 -m venv venv; fi && \
		venv/bin/pip install --upgrade pip >/dev/null && \
		venv/bin/pip install -e . >/dev/null
	@echo "📋 [4/4] Setting up Project Management (PM) server..."
	@cd submodules/julius-pm-mcp && \
		if [ ! -d venv ]; then python3 -m venv venv; fi && \
		venv/bin/pip install --upgrade pip >/dev/null && \
		venv/bin/pip install -r requirements.txt >/dev/null
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Setup complete! Run 'make install-cmd' to get the installation command."

# -------- Install Commands --------
.PHONY: install-cmd
install-cmd:
	@$(PY) scripts/generate_install_cmd.py --all

.PHONY: install-llm
install-llm:
	@$(PY) scripts/generate_install_cmd.py --server llm-prep

# -------- List Servers --------
.PHONY: list
list:
	@$(PY) scripts/generate_install_cmd.py --list

# -------- Generate Config --------
.PHONY: config
config:
	@$(PY) scripts/generate_claude_config.py

# -------- Testing / Dev --------
.PHONY: test
test:
	@$(PY) scripts/test_server.py

.PHONY: lint
lint:
	@ruff check .

.PHONY: fmt
fmt:
	@black src scripts

# -------- Diagnostics --------
.PHONY: doctor
doctor:
	@echo "🔎 Checking Python..."
	@which $(PY) || true
	@$(PY) --version
	@echo "🔎 Checking 'claude' CLI..."
	@which claude || (echo "❌ 'claude' CLI not found. Install Claude Code CLI." && exit 1)
	@echo "🔎 Checking required packages..."
	@$(PY) -c "import mcp, pydantic; print('✅ MCP & Pydantic OK')"


# -------- Cleanup --------
.PHONY: clean
clean:
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + || true
	@find . -name ".pytest_cache" -type d -prune -exec rm -rf {} + || true
	@echo "🧹 Cleaned caches."

.PHONY: reset
reset: clean
	@echo "🗑️  Removing all virtual environments..."
	@rm -rf venv
	@rm -rf submodules/*/venv
	@echo "✅ Full reset complete. Run 'make setup' to start fresh."