<# Windows PowerShell quickstart (no make needed)
   Usage:
     pwsh -File .\scripts\quickstart.ps1   (or)   powershell -File .\scripts\quickstart.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path ".\venv")) {
  py -3 -m venv venv
}

# Prefer the venv's pip
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt

Write-Host "`n✅ Virtualenv ready."
Write-Host "▶ To run the MCP server (STDIO) right now:"
Write-Host "   .\\venv\\Scripts\\python.exe src\\mcp_server_fastmcp.py --transport stdio"

Write-Host "`n▶ To add to Claude Code (Docker STDIO) from PowerShell:"
Write-Host "   docker build -f docker\\Dockerfile -t llm-context-prep-mcp:latest ."
Write-Host '   claude mcp add llm-prep -- docker run -i --rm -v "${PWD}:/workspace" llm-context-prep-mcp:latest'

Write-Host "`n▶ To run HTTP transport with docker-compose:"
Write-Host "   Copy .env.example to .env and set WORKSPACE_DIR to your project path."
Write-Host "   docker compose -f docker\\docker-compose.yml up --build"