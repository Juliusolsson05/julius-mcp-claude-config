#!/usr/bin/env python3
"""
LLM Context Preparation Tool - Core Logic
Prepares comprehensive markdown files for LLM web clients with focused context.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class LLMContextPrep:
    """Prepares focused context documents for LLM web clients."""
    
    DEFAULT_TREE_IGNORE = "bin|lib|*.log|logs|__pycache__|*.csv|*.pyc|.git|.env|*.db|node_modules|.venv|venv"
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize with project root directory."""
        self.project_root = project_root or self._find_project_root()
        self.focus_files: List[Tuple[Path, Optional[str]]] = []
        self.general_notes: List[str] = []
        self.context_dumps: List[Tuple[str, str]] = []  # (title, content)
        self.tree_ignore = self.DEFAULT_TREE_IGNORE
        self.tree_max_depth = 3  # Default tree depth
        
    def _find_project_root(self) -> Path:
        """Find project root by looking for key files."""
        current = Path.cwd()
        
        # Look for indicators of project root
        indicators = [
            'requirements.txt', 'setup.py', 'pyproject.toml',
            '.git', 'README.md', 'package.json', 'Cargo.toml',
            'go.mod', 'pom.xml', 'build.gradle'
        ]
        
        while current != current.parent:
            for indicator in indicators:
                if (current / indicator).exists():
                    return current
            current = current.parent
        
        # Default to current directory if no root found
        return Path.cwd()
    
    def add_file(self, file_path: str, note: Optional[str] = None) -> None:
        """Add a file to focus with optional note."""
        path = Path(file_path)
        
        # Make path absolute if relative
        if not path.is_absolute():
            path = self.project_root / path
        
        if not path.exists():
            print(f"⚠️  Warning: File not found: {path}")
            return
        
        self.focus_files.append((path, note))
    
    def add_general_note(self, note: str) -> None:
        """Add a general context note."""
        self.general_notes.append(note)
    
    def add_context_dump(self, title: str, content: str) -> None:
        """Add a large context dump (e.g., documentation, analysis)."""
        self.context_dumps.append((title, content))
    
    def add_context_dump_from_file(self, file_path: str, title: Optional[str] = None) -> None:
        """Add a context dump from a file."""
        path = Path(file_path)
        
        # Make path absolute if relative
        if not path.is_absolute():
            path = self.project_root / path
        
        if not path.exists():
            print(f"⚠️  Warning: Context file not found: {path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if title is None:
                title = f"Context from {path.name}"
            
            self.add_context_dump(title, content)
            print(f"✅ Added context dump from {path.name} ({len(content):,} characters)")
        except Exception as e:
            print(f"❌ Error reading context file {path}: {e}")
    
    def _generate_tree(self) -> str:
        """Generate project tree structure with focus markers."""
        # Try to use the tree command first
        cmd = ['tree', '-L', str(self.tree_max_depth), '-I', self.tree_ignore, '--charset', 'ascii']
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            tree_output = result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # tree command not available or failed
            return self._generate_simple_tree()
        
        # Mark focus files in tree
        for file_path, _ in self.focus_files:
            try:
                relative_path = file_path.relative_to(self.project_root)
                file_name = relative_path.name
                
                # Find and mark the file in tree output
                lines = tree_output.split('\n')
                for i, line in enumerate(lines):
                    if file_name in line and '[IN FOCUS]' not in line:
                        # Check if this is likely the right file
                        if str(relative_path).replace('/', os.sep) in str(self.project_root / relative_path):
                            lines[i] = line.replace(file_name, f"{file_name} [IN FOCUS]")
                            break
                tree_output = '\n'.join(lines)
            except ValueError:
                # File is outside project root
                pass
        
        return tree_output
    
    def _generate_simple_tree(self) -> str:
        """Generate a simple tree structure if tree command is not available."""
        lines = ["Project Structure:"]
        
        def should_ignore(name: str) -> bool:
            """Check if a name should be ignored based on patterns."""
            ignore_patterns = self.tree_ignore.split('|')
            for pattern in ignore_patterns:
                pattern = pattern.strip()
                # Very small glob support: *.ext, prefix*, *suffix, exact, substring
                if pattern.startswith('*.'):
                    if name.lower().endswith(pattern[1:].lower()):
                        return True
                elif pattern.endswith('/*'):
                    # directory prefix ignore (e.g., "dist/*")
                    if name.lower().startswith(pattern[:-2].lower()):
                        return True
                elif pattern.startswith('*') and not pattern.endswith('*'):
                    if name.lower().endswith(pattern[1:].lower()):
                        return True
                elif pattern.endswith('*') and not pattern.startswith('*'):
                    if name.lower().startswith(pattern[:-1].lower()):
                        return True
                elif pattern.lower() == name.lower():
                    return True
                elif pattern.lower() in name.lower():
                    return True
            return False
        
        def walk_dir(path: Path, prefix: str = "", is_last: bool = True, depth: int = 0):
            """Recursively walk directory and generate tree lines."""
            # Limit depth to prevent huge trees
            if depth >= self.tree_max_depth:
                return
            
            if path.name.startswith('.') and path.name not in ['.env', '.gitignore']:
                return  # Skip hidden files except important ones
            
            if should_ignore(path.name):
                return
            
            if path.is_file():
                # Check if this file is in focus
                marker = ""
                for focus_path, _ in self.focus_files:
                    try:
                        if path.samefile(focus_path):
                            marker = " [IN FOCUS]"
                            break
                    except:
                        pass
                
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{path.name}{marker}")
            elif path.is_dir():
                if prefix:  # Not root
                    connector = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{connector}{path.name}/")
                    new_prefix = prefix + ("    " if is_last else "│   ")
                else:
                    new_prefix = ""
                
                # Get children and sort
                try:
                    children = sorted(list(path.iterdir()), key=lambda x: (x.is_file(), x.name))
                    # Limit number of items shown
                    if len(children) > 20:
                        children = children[:20]
                        children.append(Path("... (truncated)"))
                    
                    for i, child in enumerate(children):
                        if isinstance(child, Path) and child.exists():
                            is_last_child = (i == len(children) - 1)
                            walk_dir(child, new_prefix, is_last_child, depth + 1)
                except PermissionError:
                    pass
        
        walk_dir(self.project_root)
        return '\n'.join(lines)
    
    def _format_file_content(self, file_path: Path, note: Optional[str] = None) -> str:
        """Format a file's content with header and note."""
        try:
            relative_path = file_path.relative_to(self.project_root)
        except ValueError:
            relative_path = file_path
        
        sections = []
        sections.append(f"### File: {relative_path} [IN FOCUS]")
        
        if note:
            sections.append(f"**Note:** {note}")
        
        sections.append("=" * 60)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add line numbers for code files (compact format)
            code_extensions = [
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', 
                '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
                '.r', '.m', '.h', '.hpp', '.sh', '.bash', '.zsh', '.fish'
            ]
            
            if file_path.suffix.lower() in code_extensions:
                lines = content.split('\n')
                # No padding, no trailing space after the separator — cheapest form
                numbered_lines = [f"{i}|{line}" for i, line in enumerate(lines, 1)]
                content = '\n'.join(numbered_lines)
            
            sections.append(content)
        except Exception as e:
            sections.append(f"Error reading file: {e}")
        
        sections.append("")  # Empty line after file
        return '\n'.join(sections)
    
    def generate_markdown(self) -> str:
        """Generate the complete markdown document."""
        sections = []
        
        # Header
        sections.append("# LLM Context Document")
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append(f"Project Root: {self.project_root}")
        sections.append("")
        
        # Summary Statistics
        sections.append("## Summary")
        sections.append(f"- Files in focus: {len(self.focus_files)}")
        sections.append(f"- Context dumps: {len(self.context_dumps)}")
        sections.append(f"- General notes: {len(self.general_notes)}")
        sections.append("")
        
        # Files in Focus (table format for better readability)
        if self.focus_files:
            sections.append("## Files in Focus")
            sections.append("")
            sections.append("| File | Note |")
            sections.append("|------|------|")
            for file_path, note in self.focus_files:
                try:
                    relative_path = file_path.relative_to(self.project_root)
                except ValueError:
                    relative_path = file_path
                note_text = note if note else "-"
                sections.append(f"| `{relative_path}` | {note_text} |")
            sections.append("")
        
        # Project Structure
        sections.append("## Project Structure")
        sections.append("```")
        sections.append(self._generate_tree())
        sections.append("```")
        sections.append("")
        
        # Context Dumps (before file contents for important context)
        if self.context_dumps:
            sections.append("## Context & Analysis Documents")
            sections.append("")
            for title, content in self.context_dumps:
                sections.append(f"### 📄 {title}")
                sections.append("")
                sections.append(content)
                sections.append("")
                sections.append("---")
                sections.append("")
        
        # File Contents
        if self.focus_files:
            sections.append("## File Contents")
            sections.append("")
            
            for file_path, note in self.focus_files:
                sections.append(self._format_file_content(file_path, note))
        
        # General Notes (moved to end)
        if self.general_notes:
            sections.append("## General Context & Notes")
            sections.append("")
            for i, note in enumerate(self.general_notes, 1):
                sections.append(f"**Note {i}:**")
                sections.append("")
                sections.append(note)
                sections.append("")
        
        # Footer
        sections.append("---")
        sections.append("")
        sections.append(f"*Document generated by llm-context-prep MCP server on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        sections.append("")
        sections.append("*Upload this document to Claude.ai or other web-based LLM interfaces for comprehensive analysis.*")
        
        return '\n'.join(sections)
    
    def save(self, output_path: str) -> None:
        """Save the generated markdown to a file."""
        output = Path(output_path)
        
        # Create parent directories if needed
        output.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.generate_markdown()
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Calculate some statistics
        line_count = content.count('\n')
        word_count = len(content.split())
        
        print(f"✅ Context document saved to: {output}")
        print(f"📄 Document statistics:")
        print(f"   - Size: {len(content):,} characters")
        print(f"   - Lines: {line_count:,}")
        print(f"   - Words: {word_count:,}")
        print(f"   - Files included: {len(self.focus_files)}")
        print(f"   - Context dumps: {len(self.context_dumps)}")
        print(f"   - General notes: {len(self.general_notes)}")


def load_json_config(config_path: str) -> Dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


# Standalone CLI functionality (for backwards compatibility)
def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Prepare focused context documents for LLM web clients',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with files and notes
  python llm_prep.py -f path/to/file.py "Note about this file" -n "General note" -o context.md
  
  # With context dumps
  python llm_prep.py -f main.py "Entry point" -d error_log.md "Error Analysis" -o debug_context.md
  
  # Using JSON config
  python llm_prep.py --config config.json
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        action='append',
        nargs=2,
        metavar=('PATH', 'NOTE'),
        help='Add a file with optional note (can be used multiple times)'
    )
    
    parser.add_argument(
        '--general-note', '-n',
        action='append',
        help='Add a general context note (can be used multiple times)'
    )
    
    parser.add_argument(
        '--context-dump', '-d',
        action='append',
        nargs=2,
        metavar=('FILE', 'TITLE'),
        help='Add a context dump from file with title'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Load configuration from JSON file'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='llm_context.md',
        help='Output markdown file path (default: llm_context.md)'
    )
    
    parser.add_argument(
        '--project-root', '-r',
        help='Project root directory (auto-detected if not specified)'
    )
    
    parser.add_argument(
        '--tree-ignore',
        help=f'Patterns to ignore in tree (default: {LLMContextPrep.DEFAULT_TREE_IGNORE})'
    )
    
    args = parser.parse_args()
    
    # Initialize prep tool
    project_root = Path(args.project_root) if args.project_root else None
    prep = LLMContextPrep(project_root)
    
    if args.tree_ignore:
        prep.tree_ignore = args.tree_ignore
    
    # Load from JSON config if provided
    if args.config:
        try:
            config = load_json_config(args.config)
            
            # Add files from config
            for file_entry in config.get('files', []):
                if isinstance(file_entry, dict):
                    prep.add_file(file_entry['path'], file_entry.get('note'))
                elif isinstance(file_entry, list) and len(file_entry) >= 1:
                    note = file_entry[1] if len(file_entry) > 1 else None
                    prep.add_file(file_entry[0], note)
                else:
                    prep.add_file(file_entry)
            
            # Add general notes from config
            for note in config.get('general_notes', []):
                prep.add_general_note(note)
            
            # Add context dumps from config
            for dump_entry in config.get('context_dumps', []):
                if isinstance(dump_entry, dict):
                    file_path = dump_entry.get('file')
                    title = dump_entry.get('title', f"Context from {file_path}")
                    if file_path:
                        prep.add_context_dump_from_file(file_path, title)
            
            # Override output if specified in config
            if 'output' in config:
                args.output = config['output']
                
        except Exception as e:
            print(f"❌ Error loading config file: {e}")
            sys.exit(1)
    
    # Add files from command line
    if args.file:
        for file_path, note in args.file:
            prep.add_file(file_path, note if note else None)
    
    # Add general notes from command line
    if args.general_note:
        for note in args.general_note:
            prep.add_general_note(note)
    
    # Add context dumps from command line
    if args.context_dump:
        for file_path, title in args.context_dump:
            prep.add_context_dump_from_file(file_path, title)
    
    # Check if we have any content
    if not prep.focus_files and not prep.general_notes and not prep.context_dumps:
        print("⚠️  Warning: No files, notes, or context dumps specified.")
        print("Use --file PATH NOTE, --general-note NOTE, or --context-dump FILE TITLE to add content.")
        print("Or use --config CONFIG.json to load from a configuration file.")
    
    # Generate and save
    prep.save(args.output)


if __name__ == '__main__':
    main()
