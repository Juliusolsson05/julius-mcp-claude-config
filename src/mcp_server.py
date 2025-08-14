#!/usr/bin/env python3
"""
LLM Context Preparation MCP Server
Provides tools for preparing comprehensive context documents for LLMs
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

from llm_prep import LLMContextPrep
from config import ProjectConfig, load_project_config, save_project_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMPrepMCPServer:
    """MCP Server for LLM Context Preparation"""
    
    def __init__(self):
        self.server = Server("llm-context-prep")
        self.setup_handlers()
        
    def setup_handlers(self):
        """Set up all MCP handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools"""
            return [
                Tool(
                    name="prepare_context",
                    description="Prepare comprehensive LLM context document from files and notes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project root directory"
                            },
                            "files": {
                                "type": "array",
                                "description": "List of files to include with optional notes",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string"},
                                        "note": {"type": "string"}
                                    },
                                    "required": ["path"]
                                }
                            },
                            "context_dumps": {
                                "type": "array",
                                "description": "List of markdown files to include as context dumps",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file": {"type": "string"},
                                        "title": {"type": "string"}
                                    },
                                    "required": ["file"]
                                }
                            },
                            "general_notes": {
                                "type": "array",
                                "description": "Quick context notes",
                                "items": {"type": "string"}
                            },
                            "output_name": {
                                "type": "string",
                                "description": "Output filename (saved to context_reports/)"
                            },
                            "tree_ignore": {
                                "type": "string",
                                "description": "Patterns to ignore in tree generation"
                            }
                        },
                        "required": ["project_path"]
                    }
                ),
                Tool(
                    name="create_debug_notes",
                    description="Create markdown notes file for later use as context dump",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project root"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Name of the markdown file to create"
                            },
                            "content": {
                                "type": "string",
                                "description": "Markdown content to save"
                            },
                            "subfolder": {
                                "type": "string",
                                "description": "Optional subfolder (default: .llm_prep_notes)",
                                "default": ".llm_prep_notes"
                            }
                        },
                        "required": ["project_path", "filename", "content"]
                    }
                ),
                Tool(
                    name="set_project_config",
                    description="Configure project-specific settings for context preparation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project root"
                            },
                            "tree_ignore": {
                                "type": "string",
                                "description": "Patterns to ignore in tree generation"
                            },
                            "default_output_dir": {
                                "type": "string",
                                "description": "Default directory for context reports"
                            },
                            "default_context_dumps": {
                                "type": "array",
                                "description": "Default context dumps to include",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file": {"type": "string"},
                                        "title": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["project_path"]
                    }
                ),
                Tool(
                    name="list_recent_contexts",
                    description="List recently generated context documents for a project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project root"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of recent contexts to return",
                                "default": 10
                            }
                        },
                        "required": ["project_path"]
                    }
                ),
                Tool(
                    name="clean_temp_notes",
                    description="Clean up temporary note files in .llm_prep_notes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project root"
                            },
                            "older_than_days": {
                                "type": "integer",
                                "description": "Delete files older than this many days",
                                "default": 7
                            }
                        },
                        "required": ["project_path"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "prepare_context":
                    result = await self.prepare_context(**arguments)
                elif name == "create_debug_notes":
                    result = await self.create_debug_notes(**arguments)
                elif name == "set_project_config":
                    result = await self.set_project_config(**arguments)
                elif name == "list_recent_contexts":
                    result = await self.list_recent_contexts(**arguments)
                elif name == "clean_temp_notes":
                    result = await self.clean_temp_notes(**arguments)
                else:
                    result = f"Unknown tool: {name}"
                
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @self.server.list_prompts()
        async def list_prompts() -> List[Dict]:
            """List available prompts for Claude Code"""
            prompts_file = Path(__file__).parent.parent / "prompts" / "context_prep_prompts.json"
            
            if prompts_file.exists():
                with open(prompts_file, 'r') as f:
                    prompts_data = json.load(f)
                    return prompts_data.get("prompts", [])
            
            # Default prompts if file doesn't exist
            return [
                {
                    "name": "debug_workflow",
                    "description": "Complete workflow for debugging an issue",
                    "arguments": [
                        {
                            "name": "issue_description",
                            "description": "Description of the issue to debug",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "feature_implementation",
                    "description": "Prepare context for implementing a new feature",
                    "arguments": [
                        {
                            "name": "feature_description",
                            "description": "Description of the feature to implement",
                            "required": True
                        }
                    ]
                }
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, Any]) -> Dict:
            """Get a specific prompt with arguments"""
            prompts_file = Path(__file__).parent.parent / "prompts" / "context_prep_prompts.json"
            
            if prompts_file.exists():
                with open(prompts_file, 'r') as f:
                    prompts_data = json.load(f)
                    templates = prompts_data.get("templates", {})
                    
                    if name in templates:
                        template = templates[name]
                        # Replace placeholders with arguments
                        content = template["content"]
                        for key, value in arguments.items():
                            content = content.replace(f"{{{{{key}}}}}", str(value))
                        
                        return {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {"type": "text", "text": content}
                                }
                            ]
                        }
            
            # Default prompt if not found
            if name == "debug_workflow":
                return {
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": f"""
# Debug Workflow for: {arguments.get('issue_description', 'Unknown Issue')}

Please follow these steps:

1. **Create Debug Notes**
   - First, create a markdown file with error logs and attempted solutions
   - Use the create_debug_notes tool to save this information

2. **Identify Relevant Files**
   - List all files that might be related to the issue
   - Include configuration files, error sources, and dependencies

3. **Prepare Context Document**
   - Use prepare_context tool with all relevant files and notes
   - Include the debug notes as a context dump
   - Save with a descriptive name like 'debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'

4. **Review and Upload**
   - The context document will be saved in context_reports/
   - Review it and upload to Claude.ai for deep analysis

Let's start by understanding the issue better. What error messages are you seeing?
"""
                            }
                        }
                    ]
                }
            
            return {"messages": []}
    
    async def prepare_context(
        self,
        project_path: str,
        files: Optional[List[Dict]] = None,
        context_dumps: Optional[List[Dict]] = None,
        general_notes: Optional[List[str]] = None,
        output_name: Optional[str] = None,
        tree_ignore: Optional[str] = None
    ) -> str:
        """Prepare a comprehensive context document"""
        try:
            project_path = Path(project_path).resolve()
            
            # Load project config
            config = load_project_config(project_path)
            
            # Use config defaults if not specified
            if tree_ignore is None:
                tree_ignore = config.tree_ignore
            
            # Initialize context prep
            prep = LLMContextPrep(project_root=project_path)
            if tree_ignore:
                prep.tree_ignore = tree_ignore
            
            # Add files
            if files:
                for file_info in files:
                    prep.add_file(file_info["path"], file_info.get("note"))
            
            # Add context dumps
            if context_dumps:
                for dump in context_dumps:
                    prep.add_context_dump_from_file(
                        dump["file"],
                        dump.get("title")
                    )
            
            # Add default context dumps from config
            for dump in config.default_context_dumps:
                if not any(d.get("file") == dump["file"] for d in (context_dumps or [])):
                    prep.add_context_dump_from_file(
                        dump["file"],
                        dump.get("title")
                    )
            
            # Add general notes
            if general_notes:
                for note in general_notes:
                    prep.add_general_note(note)
            
            # Determine output path
            output_dir = project_path / config.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if not output_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_name = f"context_{timestamp}.md"
            
            output_path = output_dir / output_name
            
            # Generate and save
            prep.save(str(output_path))
            
            # Update recent contexts in config
            config.recent_contexts.insert(0, {
                "timestamp": datetime.now().isoformat(),
                "output": str(output_path.relative_to(project_path)),
                "description": f"Context with {len(files or [])} files, {len(context_dumps or [])} dumps"
            })
            config.recent_contexts = config.recent_contexts[:20]  # Keep last 20
            
            save_project_config(project_path, config)
            
            return f"✅ Context document saved to: {output_path}\n📄 Size: {output_path.stat().st_size:,} bytes"
            
        except Exception as e:
            logger.error(f"Error preparing context: {e}")
            return f"❌ Error preparing context: {str(e)}"
    
    async def create_debug_notes(
        self,
        project_path: str,
        filename: str,
        content: str,
        subfolder: str = ".llm_prep_notes"
    ) -> str:
        """Create markdown notes file"""
        try:
            project_path = Path(project_path).resolve()
            notes_dir = project_path / subfolder
            notes_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure filename ends with .md
            if not filename.endswith('.md'):
                filename += '.md'
            
            file_path = notes_dir / filename
            
            # Add metadata header
            full_content = f"""---
created: {datetime.now().isoformat()}
type: debug_notes
---

{content}
"""
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            return f"✅ Created notes file: {file_path.relative_to(project_path)}"
            
        except Exception as e:
            logger.error(f"Error creating debug notes: {e}")
            return f"❌ Error creating notes: {str(e)}"
    
    async def set_project_config(
        self,
        project_path: str,
        tree_ignore: Optional[str] = None,
        default_output_dir: Optional[str] = None,
        default_context_dumps: Optional[List[Dict]] = None
    ) -> str:
        """Update project configuration"""
        try:
            project_path = Path(project_path).resolve()
            config = load_project_config(project_path)
            
            if tree_ignore is not None:
                config.tree_ignore = tree_ignore
            
            if default_output_dir is not None:
                config.output_dir = default_output_dir
            
            if default_context_dumps is not None:
                config.default_context_dumps = default_context_dumps
            
            save_project_config(project_path, config)
            
            return f"✅ Updated configuration for {project_path}"
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return f"❌ Error updating config: {str(e)}"
    
    async def list_recent_contexts(
        self,
        project_path: str,
        limit: int = 10
    ) -> str:
        """List recent context documents"""
        try:
            project_path = Path(project_path).resolve()
            config = load_project_config(project_path)
            
            if not config.recent_contexts:
                return "No recent context documents found."
            
            result = ["📚 Recent Context Documents:\n"]
            for i, ctx in enumerate(config.recent_contexts[:limit], 1):
                result.append(f"{i}. {ctx['output']}")
                result.append(f"   Created: {ctx['timestamp']}")
                result.append(f"   Description: {ctx['description']}\n")
            
            return "\n".join(result)
            
        except Exception as e:
            logger.error(f"Error listing contexts: {e}")
            return f"❌ Error listing contexts: {str(e)}"
    
    async def clean_temp_notes(
        self,
        project_path: str,
        older_than_days: int = 7
    ) -> str:
        """Clean up old temporary notes"""
        try:
            project_path = Path(project_path).resolve()
            notes_dir = project_path / ".llm_prep_notes"
            
            if not notes_dir.exists():
                return "No temporary notes directory found."
            
            cutoff_time = datetime.now().timestamp() - (older_than_days * 86400)
            deleted_count = 0
            
            for file in notes_dir.glob("*.md"):
                if file.stat().st_mtime < cutoff_time:
                    file.unlink()
                    deleted_count += 1
            
            return f"🧹 Cleaned up {deleted_count} old note files"
            
        except Exception as e:
            logger.error(f"Error cleaning notes: {e}")
            return f"❌ Error cleaning notes: {str(e)}"
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="llm-context-prep",
                    server_version="1.0.0"
                )
            )

async def main():
    """Main entry point"""
    server = LLMPrepMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
