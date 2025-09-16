#!/usr/bin/env python3
"""
LLM Context Preparation MCP Server using FastMCP
Provides tools for preparing comprehensive context documents for LLMs
"""

import os
import logging
import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

from llm_prep import LLMContextPrep
from config import (
    ProjectConfig, load_project_config, save_project_config,
    split_patterns, join_patterns, validate_ignore_patterns, normalize_patterns,
    suggest_patterns_for_project, analyze_project, server_config
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

# Enhanced Pydantic models with clear validation
class FileSpec(BaseModel):
    """Specification for a file to include in context"""
    model_config = ConfigDict(extra='allow')
    path: str = Field(description="Path relative to project root (e.g., 'src/app.py').")
    note: Optional[str] = Field(default=None, description="Note about why this file matters.")

class DumpSpec(BaseModel):
    """Specification for a context dump (markdown file)"""
    model_config = ConfigDict(extra='allow')
    file: str = Field(description="Markdown file path (e.g., '.llm_prep_notes/issue.md').")
    title: Optional[str] = Field(default=None, description="Section title for this dump.")

# Pydantic models for tool inputs
class PrepareContextInput(BaseModel):
    """Input model for prepare_context tool"""
    project_path: str = Field(description="Absolute path to project root.")
    files: Optional[List[Union[FileSpec, Dict[str, Any]]]] = Field(default=None, description="Files to include with full content.")
    context_dumps: Optional[List[Union[DumpSpec, Dict[str, Any]]]] = Field(default=None, description="Markdown notes/docs appended as sections.")
    general_notes: Optional[List[str]] = Field(default=None, description="Quick bullet notes.")
    general_note_files: Optional[List[str]] = Field(default=None, description="Append these .md files into General Notes (at end).")
    output_name: Optional[str] = Field(default=None, description="Filename saved under project's output_dir.")
    tree_ignore: Optional[str] = Field(default=None, description="Pipe-separated glob patterns (e.g., 'node_modules|*.pyc|.git').")
    tree_max_depth: Optional[int] = Field(default=3, description="Max depth for tree rendering (passed to `tree -L`).")
    dry_run: Optional[bool] = Field(default=False, description="If true, validate & preview, do not write file.")

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

class ChunkPathInput(BaseModel):
    """
    Split a directory (or glob) into multiple context markdown chunks by line count.
    Output files are named <output_basename>_1.md, _2.md, ... inside output_dir.
    The tree shown in each file is relative to the provided 'path'.
    """
    project_path: str = Field(description="Absolute path to the project root.")
    path: str = Field(description="Directory (preferred) or glob relative to project root, e.g. 'kre/services'.")
    ignore: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Ignore patterns (list or pipe/comma-separated). Examples: ['__pycache__','*.pyc','tests/*']"
    )
    line_limit: int = Field(default=3300, description="Max ~lines per output markdown (soft limit).")
    output_dir: Optional[str] = Field(default=None, description="Directory (relative to project root) to write files.")
    output_basename: Optional[str] = Field(default=None, description="Base name for outputs, e.g. 'services_summary'.")
    tree_ignore: Optional[str] = Field(default=None, description="Pipe-separated patterns to ignore in tree rendering.")
    tree_max_depth: int = Field(default=3, description="Max depth for the tree section.")
    dry_run: bool = Field(default=False, description="If true, do not write files; just report plan.")

class SaveTokensInput(BaseModel):
    """Input model for save_tokens tool - rewrites old context reports to cheaper format"""
    project_path: str = Field(description="Path to the project root")
    before: Optional[str] = Field(
        default="2025-08-22",
        description="Cutoff date (YYYY-MM-DD). Files strictly older than this are rewritten."
    )
    glob: Optional[str] = Field(
        default="**/*.md",
        description="Glob under context_reports/ to scan"
    )
    dry_run: bool = Field(
        default=True,
        description="Preview changes without writing"
    )

# Helper functions for backward compatibility and path handling
def _coerce_file_spec(d: dict) -> FileSpec:
    """Convert dict to FileSpec with synonym support"""
    if isinstance(d, FileSpec):
        return d
    return FileSpec(
        path=d.get("path") or d.get("file"),
        note=d.get("note") or d.get("notes") or d.get("comment") or d.get("description")
    )

def _coerce_dump_spec(d: dict) -> DumpSpec:
    """Convert dict to DumpSpec with synonym support"""
    if isinstance(d, DumpSpec):
        return d
    return DumpSpec(
        file=d.get("file") or d.get("path"),
        title=d.get("title") or d.get("name") or d.get("notes") or d.get("description")
    )

def _fix_path(project_path: Path, p: str) -> Path:
    """Fix common path mistakes like leading slashes"""
    raw = Path(p)
    if raw.is_absolute():
        # If absolute and under project root, allow; else try stripping leading '/'
        try:
            raw.relative_to(project_path)
            return raw
        except Exception:
            maybe = project_path / p.lstrip(os.sep)
            if maybe.exists():
                logger.warning(f"Adjusted absolute path '{p}' to project-relative '{maybe.relative_to(project_path)}'.")
                return maybe
            # Fall back to original absolute (will fail later if nonexistent)
            return raw
    return project_path / raw

# Helper functions for chunk_path_for_llm tool
def _normalize_ignore_patterns(ignore: Optional[Union[str, List[str]]]) -> List[str]:
    if not ignore:
        return []
    if isinstance(ignore, str):
        if ignore.strip().lower() in {"none", "(none)", "false", "no", ""}:
            return []
        parts = re.split(r"[|,\n]+", ignore)
    else:
        parts = ignore
    return [p.strip() for p in parts if p and p.strip()]

def _pattern_match(path: Path, root: Path, patterns: List[str]) -> bool:
    """
    Match path against glob-like patterns. We try:
      - as posix relative to 'root'
      - basename
      - full posix path
    """
    if not patterns:
        return False
    try:
        rel = path.relative_to(root).as_posix()
    except Exception:
        rel = path.as_posix()
    name = path.name
    full = path.as_posix()
    for pat in patterns:
        # Allow simple substrings as a convenience, but prefer fnmatch for globs
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(full, pat) or pat in rel:
            return True
    return False

def _gather_files_for_chunking(project_path: Path, target_root: Path, patterns: List[str]) -> List[Path]:
    """
    Collect candidate files under target_root, honoring ignore patterns and server_config
    extension/size limits. Sorted by path for determinism.
    """
    files: List[Path] = []
    # if 'target_root' is actually a glob pattern, expand it from the project root
    if ("*" in target_root.as_posix()) or ("?" in target_root.as_posix()) or ("[" in target_root.as_posix()):
        for p in project_path.glob(target_root.as_posix()):
            if p.is_file():
                if not server_config.is_file_allowed(p) or not server_config.is_file_size_allowed(p):
                    continue
                if _pattern_match(p, project_path, patterns):
                    continue
                files.append(p.resolve())
            elif p.is_dir():
                for q in p.rglob("*"):
                    if q.is_file():
                        if not server_config.is_file_allowed(q) or not server_config.is_file_size_allowed(q):
                            continue
                        if _pattern_match(q, project_path, patterns) or _pattern_match(q, p, patterns):
                            continue
                        files.append(q.resolve())
    else:
        root = target_root
        if root.is_file():
            if server_config.is_file_allowed(root) and server_config.is_file_size_allowed(root):
                if not _pattern_match(root, project_path, patterns) and not _pattern_match(root, root.parent, patterns):
                    files.append(root.resolve())
        elif root.is_dir():
            for p in root.rglob("*"):
                if p.is_file():
                    if not server_config.is_file_allowed(p) or not server_config.is_file_size_allowed(p):
                        continue
                    if _pattern_match(p, project_path, patterns) or _pattern_match(p, root, patterns):
                        continue
                    files.append(p.resolve())
    files = sorted(list(dict.fromkeys(files)))
    return files

def _count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            # sum(1 for _ in f) is memory-friendly
            return sum(1 for _ in f)
    except Exception:
        return 0

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
        
        # Set tree max depth
        prep.tree_max_depth = input.tree_max_depth or 3
        
        # Prepare lists for tracking what's included
        included_files = []
        included_dumps = []
        included_note_files = []
        
        # Add files with path fixing
        if input.files:
            for file_spec in input.files:
                # Handle both dict and FileSpec
                if isinstance(file_spec, dict):
                    file_spec = _coerce_file_spec(file_spec)
                
                # Fix path if needed
                abs_path = _fix_path(project_path, file_spec.path)
                prep.add_file(str(abs_path), file_spec.note)
                included_files.append(str(abs_path.relative_to(project_path) if abs_path.is_relative_to(project_path) else abs_path))
        
        # Add context dumps
        if input.context_dumps:
            for dump_spec in input.context_dumps:
                # Handle both dict and DumpSpec
                if isinstance(dump_spec, dict):
                    dump_spec = _coerce_dump_spec(dump_spec)
                
                prep.add_context_dump_from_file(dump_spec.file, dump_spec.title)
                included_dumps.append(dump_spec.file)
        
        # Add default context dumps from config
        for dump in config.default_context_dumps:
            if not any(d.file == dump["file"] if hasattr(d, 'file') else d.get("file") == dump["file"] 
                      for d in (input.context_dumps or [])):
                prep.add_context_dump_from_file(
                    dump["file"],
                    dump.get("title")
                )
                included_dumps.append(dump["file"])
        
        # Add general notes
        if input.general_notes:
            for note in input.general_notes:
                prep.add_general_note(note)
        
        # Append any .md files directly into General Notes (end of doc)
        if input.general_note_files:
            for path in input.general_note_files:
                p = _fix_path(project_path, path)
                try:
                    content = p.read_text(encoding="utf-8")
                    header = f"### {p.name}\n\n"
                    prep.add_general_note(header + content)
                    included_note_files.append(str(p.relative_to(project_path) if p.is_relative_to(project_path) else p))
                except Exception as e:
                    logger.warning(f"Could not read general_note_file {p}: {e}")
        
        # Handle dry-run
        if input.dry_run:
            return (
                "🧪 DRY RUN — no file written\n"
                f"• Files in focus ({len(included_files)}):\n  - " + "\n  - ".join(included_files or ["(none)"]) + "\n"
                f"• Context dumps:\n  - " + "\n  - ".join(included_dumps or ["(none)"]) + "\n"
                f"• General note files (end):\n  - " + "\n  - ".join(included_note_files or ["(none)"]) + "\n"
                f"• tree_max_depth={prep.tree_max_depth}\n"
                f"• tree_ignore='{prep.tree_ignore}'"
            )
        
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
            "description": f"Context with {len(included_files)} files, {len(included_dumps)} dumps"
        })
        config.recent_contexts = config.recent_contexts[:20]  # Keep last 20
        
        save_project_config(project_path, config)
        
        # Return standardized success output
        return (
            f"✅ Context document saved to: {output_path}\n"
            f"📄 Size: {output_path.stat().st_size:,} bytes\n"
            f"• Files in focus ({len(included_files)}):\n  - " + "\n  - ".join(included_files or ["(none)"]) + "\n"
            f"• Context dumps:\n  - " + "\n  - ".join(included_dumps or ["(none)"]) + "\n"
            f"• General note files (end):\n  - " + "\n  - ".join(included_note_files or ["(none)"])
        )
        
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
async def get_server_limits() -> str:
    """Get server limits for file size and context size"""
    return (
        f"Max file size: {server_config.max_file_size:,} bytes\n"
        f"Max context size: {server_config.max_context_size:,} bytes\n"
        f"Allowed extensions: {', '.join(server_config.allowed_extensions)}"
    )

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

@mcp.tool()
async def chunk_path_for_llm(input: ChunkPathInput) -> str:
    """
    Split a directory (or glob) into multiple context markdown chunks by line-count.
    Each chunk renders a tree relative to the provided 'path' and the files are included
    exactly like in prepare_context (same headers, numbered lines, etc.).
    """
    try:
        project_path = Path(input.project_path).resolve()
        config = load_project_config(project_path)

        # Resolve the target root (dir or glob), relative to project
        raw = Path(input.path)
        target_root = (project_path / raw).resolve() if not raw.is_absolute() else raw.resolve()

        if not target_root.exists() and ("*" not in target_root.as_posix()):
            return f"❌ Path not found: {target_root}"

        # Ignore patterns for selection (NOT the same as tree_ignore, though we apply them to tree too)
        ignore_patterns = _normalize_ignore_patterns(input.ignore)

        # Tree ignore for rendering
        base_tree_ignore = input.tree_ignore or config.tree_ignore or ""
        tree_ign_list = split_patterns(base_tree_ignore)
        # merge input ignore patterns into tree ignore so the tree hides them as well
        merged_tree_ignore = join_patterns(tree_ign_list + ignore_patterns) if ignore_patterns else base_tree_ignore

        # Gather candidate files
        files = _gather_files_for_chunking(project_path, target_root, ignore_patterns)
        if not files:
            return "⚠️ No matching files after applying ignores/filters."

        # Plan chunking
        line_limit = max(500, int(input.line_limit))  # guardrails: don't let it be too tiny
        safety_margin = 300  # room for headers, tables, tree, footer
        per_file_overhead = 4  # section header + separator + trailing newline(s)

        # Output directory & base name
        out_dir = Path(input.output_dir).resolve() if input.output_dir and Path(input.output_dir).is_absolute() \
            else (project_path / (input.output_dir or config.output_dir)).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        default_base = (Path(input.path).name or "chunk")
        base_name = input.output_basename or (default_base.rstrip("/").rstrip("\\") + "_summary")

        # Build chunks
        chunks: List[List[Path]] = []
        current: List[Path] = []
        used = 0

        for p in files:
            lines = _count_lines(p)
            # if starting a fresh chunk, allow a single huge file as its own chunk
            if not current and (lines + per_file_overhead > (line_limit - safety_margin)):
                chunks.append([p])
                used = 0
                continue

            # would adding this file overflow the chunk?
            if used + lines + per_file_overhead > (line_limit - safety_margin):
                if current:
                    chunks.append(current)
                current = [p]
                used = lines + per_file_overhead
            else:
                current.append(p)
                used += lines + per_file_overhead

        if current:
            chunks.append(current)

        # Dry run report
        if input.dry_run:
            report = [
                f"🧪 DRY RUN — chunk plan for {target_root}",
                f"Files considered: {len(files)}",
                f"line_limit={line_limit}, safety_margin={safety_margin}, tree_max_depth={input.tree_max_depth}",
                f"Output dir: {out_dir}",
                "",
            ]
            for i, group in enumerate(chunks, 1):
                approx = sum(_count_lines(f) + per_file_overhead for f in group) + safety_margin
                rp = "\n  - ".join([str(f.relative_to(project_path)) for f in group])
                report.append(f"Chunk {i} (~{approx} lines):\n  - {rp}")
            return "\n".join(report)

        # Write chunks using LLMContextPrep so formatting/tree are identical
        outputs: List[str] = []
        for i, group in enumerate(chunks, 1):
            # Make the tree relative to the requested path (subtree)
            # If 'target_root' is a file or a glob, show tree from its parent
            sub_root = target_root if target_root.is_dir() else target_root.parent
            prep = LLMContextPrep(project_root=sub_root if sub_root.exists() else project_path)
            prep.tree_ignore = merged_tree_ignore
            prep.tree_max_depth = input.tree_max_depth

            for fpath in group:
                # absolute ok; LLMContextPrep will compute relative to project_root
                prep.add_file(str(fpath))

            filename = f"{base_name}_{i}.md"
            prep.save(str(out_dir / filename))
            outputs.append(str((out_dir / filename).relative_to(project_path)))

        summary = [
            f"✅ Created {len(outputs)} chunk(s) from {target_root}",
            f"Output directory: {out_dir.relative_to(project_path)}",
            "",
            "Files:",
            *[f"  - {o}" for o in outputs]
        ]
        return "\n".join(summary)

    except Exception as e:
        logger.error(f"chunk_path_for_llm error: {e}")
        return f"❌ Error: {e}"

@mcp.tool()
async def save_tokens(input: SaveTokensInput) -> str:
    """
    Rewrite old context_reports to cheaper line-number format.
    Converts leading padded numbers like '   1| ' to '1|' (no padding, no trailing space).
    Only touches files modified before the given cutoff date.
    """
    try:
        project_path = Path(input.project_path).resolve()
        reports_dir = project_path / "context_reports"
        if not reports_dir.exists():
            return "⚠️ No context_reports/ directory found."

        # Parse cutoff date (YYYY-MM-DD)
        cutoff = datetime.strptime(input.before, "%Y-%m-%d")
        cutoff_ts = cutoff.timestamp()

        # Pattern: start-of-line, up to 6 spaces, digits, pipe, optional single space
        # Replace with: digits + '|' (no trailing space)
        pattern = re.compile(r"(?m)^\s{0,6}(\d+)\|\s")
        
        total_files = 0
        touched = 0
        total_chars_saved = 0

        for md in reports_dir.glob(input.glob):
            if not md.is_file():
                continue
            total_files += 1
            try:
                if md.stat().st_mtime >= cutoff_ts:
                    continue  # not older than cutoff

                original = md.read_text(encoding="utf-8", errors="ignore")
                new = pattern.sub(r"\1|", original)
                if new != original:
                    touched += 1
                    saved = len(original) - len(new)
                    total_chars_saved += saved
                    if not input.dry_run:
                        md.write_text(new, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Skipped {md}: {e}")

        mode = "DRY RUN" if input.dry_run else "UPDATED"
        return (
            f"✅ save_tokens {mode}\n"
            f"Scanned: {total_files} files under context_reports/\n"
            f"Changed: {touched} files (cutoff < {input.before})\n"
            f"Approx chars saved: {total_chars_saved:,}\n"
            f"Rule: '^(spaces)(digits)|␣'  ->  'digits|'"
        )
    except Exception as e:
        logger.error(f"save_tokens error: {e}")
        return f"❌ Error: {e}"

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
async def notes_first(task_title: str, objectives: str) -> str:
    """Guided workflow for creating notes before context"""
    return f"""
# Notes-First Workflow: {task_title}

## Objectives:
{objectives}

## Step 1: Create Your Notes

I'll help you create structured notes first. Use `create_debug_notes` with:
```
project_path: "[your project path]"
filename: "{task_title}_notes.md"
content: "[your markdown content]"
```

## Step 2: Ready-to-Use Context Template

Once your notes are saved, here's your `prepare_context` template:

```json
{{
  "project_path": "[your project path]",
  "dry_run": true,
  "output_name": "{task_title}_context.md",
  "files": [
    {{"path": "src/main.py", "note": "Entry point"}},
    {{"path": "config/settings.py", "note": "Configuration"}}
  ],
  "context_dumps": [
    {{"file": ".llm_prep_notes/{task_title}_notes.md", "title": "Analysis Notes"}}
  ],
  "general_note_files": [
    ".llm_prep_notes/additional_notes.md"
  ],
  "tree_max_depth": 3
}}
```

## Step 3: Two-Phase Execution

1. **Preview**: Run with `dry_run: true` to verify what will be included
2. **Generate**: If preview looks good, run with `dry_run: false`

## Tips:
- Replace placeholder paths with your actual relative paths
- Add/remove files as needed for your specific task
- Adjust tree_max_depth if you need deeper directory structure

What information would you like to capture in your notes?
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
        choices=["stdio", "http", "sse"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport type: stdio (default), http, or sse"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_SERVER_PORT", "8847")),
        help="Port for HTTP/SSE server (default: 8847 or MCP_SERVER_PORT env)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_SERVER_HOST", "127.0.0.1"),
        help="Host for HTTP/SSE server (default: 127.0.0.1 or MCP_SERVER_HOST env)"
    )
    
    args = parser.parse_args()
    
    # Run with appropriate transport mode
    if args.transport == "stdio":
        # STDIO mode doesn't need host/port
        mcp.run(transport="stdio")
    else:
        # HTTP/SSE modes use host and port
        mcp.run(
            transport=args.transport,
            host=args.host,
            port=args.port
        )

if __name__ == "__main__":
    main()