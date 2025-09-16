@echo off
REM Windows CMD quickstart (no make needed)
IF NOT EXIST venv (
  py -3 -m venv venv
)
call venv\Scripts\python.exe -m pip install --upgrade pip
call venv\Scripts\pip.exe install -r requirements.txt

echo/
echo ✅ Virtualenv ready.
echo ▶ Run MCP server (STDIO):
echo    venv\Scripts\python.exe src\mcp_server_fastmcp.py --transport stdio
echo/
echo ▶ Add to Claude Code (Docker STDIO):
echo    docker build -f docker\Dockerfile -t llm-context-prep-mcp:latest .
echo    claude mcp add llm-prep -- docker run -i --rm -v "%%cd%%:/workspace" llm-context-prep-mcp:latest
echo/
echo ▶ HTTP transport with docker-compose:
echo    Copy .env.example to .env and set WORKSPACE_DIR
echo    docker compose -f docker\docker-compose.yml up --build