#!/usr/bin/env python3
"""
Generate Claude Desktop configuration for all MCP servers from mcp-servers.json.
Outputs JSON configuration that can be added to claude_desktop_config.json
"""

import json
import os
import sys
import platform
import subprocess
from pathlib import Path


def get_claude_config_path():
    """Get the path to Claude Desktop configuration file"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        config_home = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(config_home) / "Claude" / "claude_desktop_config.json"
    
    return None


def load_config():
    """Load MCP servers configuration"""
    config_path = Path(__file__).parent.parent / "mcp-servers.json"
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path) as f:
        return json.load(f)


def generate_config():
    """Generate MCP server configuration for all servers from config file"""
    base_path = Path(__file__).parent.parent.absolute()
    mcp_config = load_config()
    
    config = {"mcpServers": {}}
    
    for server in mcp_config["servers"]:
        if server["type"] == "local":
            python_path = base_path / server["python_path"]
            script_path = base_path / server["script_path"]
            
            # Check if venv exists, fallback to system python
            if not python_path.exists():
                python_path = "python3"
            
            config["mcpServers"][server["name"]] = {
                "command": str(python_path),
                "args": [str(script_path)] + server["args"]
            }
            
        elif server["type"] == "submodule":
            python_path = base_path / server["python_path"]
            
            # Check if venv exists, fallback to system python
            if not python_path.exists():
                python_path = "python3"
            
            config["mcpServers"][server["name"]] = {
                "command": str(python_path),
                "args": ["-m", server["module"]] + server["args"]
            }
    
    return config


def copy_to_clipboard(text):
    """Copy text to system clipboard"""
    try:
        # macOS
        if platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        # Linux (X11)
        elif subprocess.run(["which", "xclip"], capture_output=True).returncode == 0:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            return True
        # Linux (Wayland)
        elif subprocess.run(["which", "wl-copy"], capture_output=True).returncode == 0:
            subprocess.run(["wl-copy"], input=text.encode(), check=True)
            return True
        # Windows
        elif platform.system() == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True)
            return True
    except Exception:
        pass
    return False


def main():
    config = generate_config()
    config_json = json.dumps(config, indent=2)
    
    print("🔧 Generated Claude Desktop configuration:")
    print("=" * 60)
    print(config_json)
    print("=" * 60)
    
    config_path = get_claude_config_path()
    if config_path:
        print(f"\n📍 Your Claude config file is at:")
        print(f"   {config_path}")
        
        if config_path.exists():
            print("\n⚠️  Config file exists. You'll need to merge this configuration.")
            print("   The 'mcpServers' section should be added/updated in your existing config.")
        else:
            print("\n📝 Config file doesn't exist yet. You can create it with the above content.")
    
    # Try to copy to clipboard
    if copy_to_clipboard(config_json):
        print("\n✅ Configuration copied to clipboard!")
        print("   Paste it into your claude_desktop_config.json file.")
    else:
        print("\n📋 Copy the configuration above to your claude_desktop_config.json file.")
    
    print("\n🚀 After updating the config, restart Claude Desktop to load the MCP servers.")


if __name__ == "__main__":
    main()