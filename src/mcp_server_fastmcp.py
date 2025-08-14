#!/usr/bin/env python3
"""
LLM Context Preparation MCP Server using FastMCP
Provides tools for preparing comprehensive context documents for LLMs
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from llm_prep import LLMContextPrep
from config import (
    ProjectConfig, load_project_config, save_project_config,
    split_patterns, join_patterns, validate_ignore_patterns, normalize_patterns,
    suggest_patterns_for_project, analyze_project
)
from typing import Literal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("llm-context-prep")

# Pydantic models for tool inputs
class PrepareContextInput(BaseModel):
    """Input model for prepare_context tool"""
    project_path: str = Field(description="Path to the project root directory")
    files: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of files to include with optional notes")
    context_dumps: Optional[List[Dict[str, str]]] = Field(default=None, description="List of markdown files to include as context dumps")
    general_notes: Optional[List[str]] = Field(default=None, description="Quick context notes")
    output_name: Optional[str] = Field(default=None, description="Output filename (saved to context_reports/)")
    tree_ignore: Optional[str] = Field(default=None, description="Patterns to ignore in tree generation")

class CreateDebugNotesInput(BaseModel):
    """Input model for create_debug_notes tool"""
    project_path: str = Field(description="Path to the project root")
    filename: str = Field(description="Name of the markdown file to create")
    content: str = Field(description="Markdown content to save")
    subfolder: str = Field(default=".llm_prep_notes", description="Optional subfolder")

class SetProjectConfigInput(BaseModel):
    """Input model for set_project_config tool"""
    project_path: str = Field(description="Path to the project root")
    tree_ignore: Optional[str] = Field(default=None, description="Patterns to ignore in tree generation")
    default_output_dir: Optional[str] = Field(default=None, description="Default directory for context reports")
    default_context_dumps: Optional[List[Dict[str, str]]] = Field(default=None, description="Default context dumps to include")

class ListRecentContextsInput(BaseModel):
    """Input model for list_recent_contexts tool"""
    project_path: str = Field(description="Path to the project root")
    limit: int = Field(default=10, description="Maximum number of recent contexts to return")

class CleanTempNotesInput(BaseModel):
    """Input model for clean_temp_notes tool"""
    project_path: str = Field(description="Path to the project root")
    older_than_days: int = Field(default=7, description="Delete files older than this many days")

class GetTreeIgnoreInput(BaseModel):
    project_path: str = Field(description="Path to the project root")

class UpdateTreeIgnoreInput(BaseModel):
    project_path: str = Field(description="Path to the project root")
    action: Literal["set","add","remove","auto"] = Field(default="add", description="How to apply changes")
    patterns: Optional[List[str]] = Field(default=None, description="Patterns for set/add/remove")
    auto_detect: bool = Field(default=False, description="If true, analyze project to select patterns")
    reason: Optional[str] = Field(default=None, description="Why this change is made (stored in history)")

class AnalyzeProjectInput(BaseModel):
    project_path: str = Field(description="Path to the project root")

# Tools
@mcp.tool()
async def prepare_context(input: PrepareContextInput) -> str:
    """Prepare comprehensive LLM context document from files and notes"""
    try:
        project_path = Path(input.project_path).resolve()
        
        # Load project config
        config = load_project_config(project_path)
        
        # Use config defaults if not specified
        tree_ignore = input.tree_ignore or config.tree_ignore
        
        # Initialize context prep
        prep = LLMContextPrep(project_root=project_path)
        if tree_ignore:
            prep.tree_ignore = tree_ignore
        
        # Add files
        if input.files:
            for file_info in input.files:
                prep.add_file(file_info["path"], file_info.get("note"))
        
        # Add context dumps
        if input.context_dumps:
            for dump in input.context_dumps:
                prep.add_context_dump_from_file(
                    dump["file"],
                    dump.get("title")
                )
        
        # Add default context dumps from config
        for dump in config.default_context_dumps:
            if not any(d.get("file") == dump["file"] for d in (input.context_dumps or [])):
                prep.add_context_dump_from_file(
                    dump["file"],
                    dump.get("title")
                )
        
        # Add general notes
        if input.general_notes:
            for note in input.general_notes:
                prep.add_general_note(note)
        
        # Determine output path
        output_dir = project_path / config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input.output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"context_{timestamp}.md"
        else:
            output_name = input.output_name
        
        output_path = output_dir / output_name
        
        # Generate and save
        prep.save(str(output_path))
        
        # Update recent contexts in config
        config.recent_contexts.insert(0, {
            "timestamp": datetime.now().isoformat(),
            "output": str(output_path.relative_to(project_path)),
            "description": f"Context with {len(input.files or [])} files, {len(input.context_dumps or [])} dumps"
        })
        config.recent_contexts = config.recent_contexts[:20]  # Keep last 20
        
        save_project_config(project_path, config)
        
        return f"✅ Context document saved to: {output_path}\n📄 Size: {output_path.stat().st_size:,} bytes"
        
    except Exception as e:
        logger.error(f"Error preparing context: {e}")
        return f"❌ Error preparing context: {str(e)}"

@mcp.tool()
async def create_debug_notes(input: CreateDebugNotesInput) -> str:
    """Create markdown notes file for later use as context dump"""
    try:
        project_path = Path(input.project_path).resolve()
        notes_dir = project_path / input.subfolder
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure filename ends with .md
        filename = input.filename
        if not filename.endswith('.md'):
            filename += '.md'
        
        file_path = notes_dir / filename
        
        # Add metadata header
        full_content = f"""---
created: {datetime.now().isoformat()}
type: debug_notes
---

{input.content}
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return f"✅ Created notes file: {file_path.relative_to(project_path)}"
        
    except Exception as e:
        logger.error(f"Error creating debug notes: {e}")
        return f"❌ Error creating notes: {str(e)}"

@mcp.tool()
async def set_project_config(input: SetProjectConfigInput) -> str:
    """Configure project-specific settings for context preparation"""
    try:
        project_path = Path(input.project_path).resolve()
        config = load_project_config(project_path)
        
        if input.tree_ignore is not None:
            config.tree_ignore = input.tree_ignore
        
        if input.default_output_dir is not None:
            config.output_dir = input.default_output_dir
        
        if input.default_context_dumps is not None:
            config.default_context_dumps = input.default_context_dumps
        
        save_project_config(project_path, config)
        
        return f"✅ Updated configuration for {project_path}"
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return f"❌ Error updating config: {str(e)}"

@mcp.tool()
async def list_recent_contexts(input: ListRecentContextsInput) -> str:
    """List recently generated context documents for a project"""
    try:
        project_path = Path(input.project_path).resolve()
        config = load_project_config(project_path)
        
        if not config.recent_contexts:
            return "No recent context documents found."
        
        result = ["📚 Recent Context Documents:\n"]
        for i, ctx in enumerate(config.recent_contexts[:input.limit], 1):
            result.append(f"{i}. {ctx['output']}")
            result.append(f"   Created: {ctx['timestamp']}")
            result.append(f"   Description: {ctx['description']}\n")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error listing contexts: {e}")
        return f"❌ Error listing contexts: {str(e)}"

@mcp.tool()
async def clean_temp_notes(input: CleanTempNotesInput) -> str:
    """Clean up temporary note files in .llm_prep_notes"""
    try:
        project_path = Path(input.project_path).resolve()
        notes_dir = project_path / ".llm_prep_notes"
        
        if not notes_dir.exists():
            return "No temporary notes directory found."
        
        cutoff_time = datetime.now().timestamp() - (input.older_than_days * 86400)
        deleted_count = 0
        
        for file in notes_dir.glob("*.md"):
            if file.stat().st_mtime < cutoff_time:
                file.unlink()
                deleted_count += 1
        
        return f"🧹 Cleaned up {deleted_count} old note files"
        
    except Exception as e:
        logger.error(f"Error cleaning notes: {e}")
        return f"❌ Error cleaning notes: {str(e)}"

@mcp.tool()
async def get_tree_ignore(input: GetTreeIgnoreInput) -> str:
    """Get current tree ignore patterns and suggestions."""
    try:
        project_path = Path(input.project_path).resolve()
        config = load_project_config(project_path)
        current = split_patterns(config.tree_ignore)
        info = analyze_project(project_path)
        sugg = suggest_patterns_for_project(project_path)

        recommended_adds = [p for p in (sugg["critical"] + sugg["recommended"]) if p.lower() not in {c.lower() for c in current}]
        summary = [
            f"📁 Project: {project_path}",
            f"🧠 Detected project type: {info['project_type']}",
            "",
            "Current ignore patterns:",
            f"  " + (config.tree_ignore or "(none)"),
            "",
            "Suggested additions (critical + recommended):",
            ("  " + ", ".join(recommended_adds)) if recommended_adds else "  (none)",
        ]
        return "\n".join(summary)
    except Exception as e:
        logger.error(f"get_tree_ignore error: {e}")
        return f"❌ Error: {e}"

@mcp.tool()
async def update_tree_ignore(input: UpdateTreeIgnoreInput) -> str:
    """Update tree ignore patterns with intelligent suggestions & history."""
    try:
        project_path = Path(input.project_path).resolve()
        config = load_project_config(project_path)
        now = datetime.now().isoformat()

        current = split_patterns(config.tree_ignore)
        result_msg = ""

        if input.action == "auto":
            sugg = suggest_patterns_for_project(project_path)
            new_list = normalize_patterns(sugg["critical"] + sugg["recommended"])
            v = validate_ignore_patterns(new_list)
            if v["errors"]:
                return "❌ " + "; ".join(v["errors"])
            config.tree_ignore = v["joined"]
            config.project_type = analyze_project(project_path)["project_type"]
            config.auto_detected_patterns = new_list
            result_msg = f"Auto-configured patterns ({len(new_list)}): {config.tree_ignore}"

        elif input.action in {"set", "add", "remove"}:
            patterns = normalize_patterns(input.patterns or [])
            if input.action == "set":
                v = validate_ignore_patterns(patterns)
                if v["errors"]:
                    return "❌ " + "; ".join(v["errors"])
                config.tree_ignore = v["joined"]
                result_msg = f"Set patterns to: {config.tree_ignore}"

            elif input.action == "add":
                merged = current + [p for p in patterns if p.lower() not in {c.lower() for c in current}]
                v = validate_ignore_patterns(merged)
                if v["errors"]:
                    return "❌ " + "; ".join(v["errors"])
                config.tree_ignore = v["joined"]
                result_msg = f"Added: {', '.join(patterns)}"

            else:  # remove
                lower_remove = {p.lower() for p in patterns}
                remaining = [p for p in current if p.lower() not in lower_remove]
                v = validate_ignore_patterns(remaining)
                # removing can't create errors except length; still check
                config.tree_ignore = v["joined"]
                result_msg = f"Removed: {', '.join(patterns)}"

        else:
            return "❌ Unknown action"

        # record history
        config.tree_ignore_history = config.tree_ignore_history or []
        config.tree_ignore_history.insert(0, {
            "timestamp": now,
            "patterns": config.tree_ignore,
            "action": input.action,
            "reason": input.reason or "",
        })
        config.tree_ignore_history = config.tree_ignore_history[:50]

        save_project_config(project_path, config)

        # surface warnings if any
        warnings = validate_ignore_patterns(split_patterns(config.tree_ignore))["warnings"]
        warn_block = ("\n⚠️  " + "\n⚠️  ".join(warnings)) if warnings else ""
        return f"✅ {result_msg}{warn_block}"

    except Exception as e:
        logger.error(f"update_tree_ignore error: {e}")
        return f"❌ Error updating tree ignore: {e}"

@mcp.tool()
async def analyze_project_structure(input: AnalyzeProjectInput) -> str:
    """Analyze project and suggest optimal ignore patterns."""
    try:
        project_path = Path(input.project_path).resolve()
        info = analyze_project(project_path)
        sugg = suggest_patterns_for_project(project_path)

        lines = [
            f"📁 Project: {project_path}",
            f"🧠 Detected type: {info['project_type']}",
            "",
            "Indicators:",
            f"  {info['indicators']}",
            f"Build tools: {', '.join(info['build_tools']) if info['build_tools'] else '(none)'}",
            "",
            "Large directories (>100MB):"
        ]
        if info["big_dirs"]:
            for d in info["big_dirs"]:
                lines.append(f"  - {d['name']} ~ {d['bytes']:,} bytes")
        else:
            lines.append("  (none)")

        lines += [
            "",
            "Compiled/binary footprints found:",
            f"  {', '.join(info['compiled_present']) if info['compiled_present'] else '(none)'}",
            "",
            "Suggested patterns:",
            f"  critical: {', '.join(sugg['critical']) or '(none)'}",
            f"  recommended: {', '.join(sugg['recommended']) or '(none)'}",
            f"  optional: {', '.join(sugg['optional']) or '(none)'}",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"analyze_project_structure error: {e}")
        return f"❌ Error analyzing project: {e}"

# Prompts
@mcp.prompt()
async def debug_workflow(issue_description: str) -> str:
    """Complete workflow for debugging an issue"""
    return f"""
# Debug Workflow for: {issue_description}

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

@mcp.prompt()
async def feature_implementation(feature_description: str) -> str:
    """Prepare context for implementing a new feature"""
    return f"""
# Feature Implementation: {feature_description}

To implement this feature effectively, let's gather the necessary context:

1. **Identify Related Components**
   - List existing files that relate to this feature
   - Include similar features for reference
   - Add configuration and dependency files

2. **Document Requirements**
   - Create a notes file with feature requirements
   - Include acceptance criteria and constraints
   - Add any relevant API documentation

3. **Prepare Implementation Context**
   - Use prepare_context with all relevant files
   - Include the requirements notes
   - Add any design documents or specifications

The context document will help ensure a complete and consistent implementation.
"""

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Context Prep MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport type (stdio only)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_SERVER_PORT", "8847")),
        help="Port for SSE server (default: 8847 or MCP_SERVER_PORT env)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE server (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()