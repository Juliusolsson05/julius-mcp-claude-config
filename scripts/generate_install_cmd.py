#!/usr/bin/env python3
"""
Generate Claude MCP installation commands from mcp-servers.json config
"""

import json
import sys
import argparse
import subprocess
import platform
from pathlib import Path


def load_config():
    """Load MCP servers configuration"""
    config_path = Path(__file__).parent.parent / "mcp-servers.json"
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path) as f:
        return json.load(f)


def get_server_command(server, base_path):
    """Generate the claude mcp add command for a single server"""
    if server["type"] == "local":
        python_path = base_path / server["python_path"]
        script_path = base_path / server["script_path"]
        args = " ".join([f'"{arg}"' for arg in server["args"]])
        return f'claude mcp add {server["name"]} -- "{python_path}" "{script_path}" {args}'.strip()
    
    elif server["type"] == "submodule":
        python_path = base_path / server["python_path"]
        args = " ".join([f'"{arg}"' for arg in server["args"]])
        return f'claude mcp add {server["name"]} -- "{python_path}" -m {server["module"]} {args}'.strip()
    
    return None


def generate_combined_command(servers, base_path):
    """Generate a combined command for all servers"""
    commands = []
    for server in servers:
        cmd = get_server_command(server, base_path)
        if cmd:
            commands.append(cmd)
    
    return " && ".join(commands)


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


def list_servers(config):
    """List all configured MCP servers"""
    print("\n📦 Configured MCP Servers")
    print("=" * 60)
    for i, server in enumerate(config["servers"], 1):
        print(f"\n{i}. {server['name']}")
        print(f"   Type: {server['type']}")
        print(f"   Description: {server['description']}")
    print("\n" + "=" * 60)
    print(f"Total: {len(config['servers'])} servers")


def main():
    parser = argparse.ArgumentParser(description="Generate Claude MCP installation commands")
    parser.add_argument("--all", action="store_true", help="Generate command for all servers")
    parser.add_argument("--server", help="Generate command for specific server")
    parser.add_argument("--list", action="store_true", help="List all configured servers")
    parser.add_argument("--no-copy", action="store_true", help="Don't copy to clipboard")
    
    args = parser.parse_args()
    
    # Default to --all if no arguments
    if not args.all and not args.server and not args.list:
        args.all = True
    
    config = load_config()
    base_path = Path(__file__).parent.parent.absolute()
    
    if args.list:
        list_servers(config)
        return
    
    if args.server:
        # Find specific server
        server = next((s for s in config["servers"] if s["name"] == args.server), None)
        if not server:
            print(f"❌ Server '{args.server}' not found in configuration")
            print("Available servers:")
            for s in config["servers"]:
                print(f"  - {s['name']}")
            sys.exit(1)
        
        command = get_server_command(server, base_path)
        print(f"\n📦 Installation command for {server['name']}:")
    else:
        # Generate for all servers
        command = generate_combined_command(config["servers"], base_path)
        print("\n📦 Installation command for ALL servers:")
    
    print("=" * 60)
    print(command)
    print("=" * 60)
    
    if not args.no_copy and copy_to_clipboard(command):
        print("\n✅ Command copied to clipboard!")
        print("   Paste and run it in your terminal.")
    else:
        print("\n📋 Copy the command above and run it in your terminal.")
    
    print("\n💡 After running, restart Claude Desktop to load the MCP servers.")


if __name__ == "__main__":
    main()