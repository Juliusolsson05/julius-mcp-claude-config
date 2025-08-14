# -------- Config --------
PY ?= venv/bin/python
PIP ?= venv/bin/pip

# -------- Help --------
.PHONY: help
help:
	@echo ""
	@echo "LLM Context Prep – Make targets"
	@echo "--------------------------------"
	@echo "make bootstrap        Create venv and install deps"
	@echo "make claude-stdio-cmd Print STDIO add command (ask to copy)"
	@echo "make claude-add       Execute the STDIO add command now"
	@echo "make test             Run quick test script"
	@echo "make lint             Run ruff"
	@echo "make fmt              Run black"
	@echo "make doctor           Sanity checks (python, claude, pkgs)"
	@echo "make clean            Remove caches"
	@echo "make distclean        Remove venv + caches"
	@echo ""

# -------- Bootstrap --------
.PHONY: bootstrap
bootstrap:
	@echo "🐍 Creating venv (if needed) and installing requirements..."
	@if [ ! -d venv ]; then python3 -m venv venv; fi
	@$(PIP) install --upgrade pip >/dev/null
	@$(PIP) install -r requirements.txt
	@echo "✅ Done."

# -------- Claude STDIO command (with clipboard prompt) --------
.PHONY: claude-stdio-cmd
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

# -------- Directly add to Claude (no copy/paste needed) --------
.PHONY: claude-add
claude-add:
	@BASE=$$(pwd -P); \
	if [ -x venv/bin/python ]; then PY="$$BASE/venv/bin/python"; \
	elif command -v python3 >/dev/null 2>&1; then PY=$$(command -v python3); \
	else PY=$$(command -v python); fi; \
	SCRIPT="$$BASE/src/mcp_server_fastmcp.py"; \
	claude mcp add llm-prep -- "$$PY" "$$SCRIPT" --transport stdio

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

.PHONY: distclean
distclean: clean
	@rm -rf venv
	@echo "🧹 Removed venv."