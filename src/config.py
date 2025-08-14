#!/usr/bin/env python3
"""
Configuration management for LLM Context Prep MCP Server
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field, fields
from datetime import datetime
from collections import defaultdict


@dataclass
class ProjectConfig:
    """Configuration for a specific project"""
    tree_ignore: str = "bin|lib|*.log|logs|__pycache__|*.csv|*.pyc|.git|.env|*.db|node_modules|.venv|venv"
    output_dir: str = "context_reports"
    default_context_dumps: List[Dict[str, str]] = field(default_factory=list)
    recent_contexts: List[Dict[str, Any]] = field(default_factory=list)
    # NEW: per-project smart ignore metadata
    tree_ignore_history: List[Dict[str, Any]] = field(default_factory=list)
    project_type: Optional[str] = None
    auto_detected_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectConfig':
        """Create from dictionary"""
        defaults = {f.name: f.default for f in fields(cls) if f.default is not field}
        return cls(
            tree_ignore=data.get('tree_ignore', defaults.get('tree_ignore', "bin|lib|*.log|logs|__pycache__|*.csv|*.pyc|.git|.env|*.db|node_modules|.venv|venv")),
            output_dir=data.get('output_dir', defaults.get('output_dir', "context_reports")),
            default_context_dumps=data.get('default_context_dumps', []),
            recent_contexts=data.get('recent_contexts', []),
            tree_ignore_history=data.get('tree_ignore_history', []),
            project_type=data.get('project_type'),
            auto_detected_patterns=data.get('auto_detected_patterns', [])
        )


def get_config_path(project_path: Path) -> Path:
    """Get the configuration file path for a project"""
    return project_path / '.llm_prep_config.json'


def load_project_config(project_path: Path) -> ProjectConfig:
    """Load configuration for a project, creating default if doesn't exist"""
    config_path = get_config_path(project_path)
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ProjectConfig.from_dict(data)
        except Exception as e:
            print(f"⚠️  Warning: Error loading config from {config_path}: {e}")
            print("Using default configuration")
    
    # Return default config if file doesn't exist or error occurred
    return ProjectConfig()


def save_project_config(project_path: Path, config: ProjectConfig) -> None:
    """Save configuration for a project"""
    config_path = get_config_path(project_path)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Warning: Error saving config to {config_path}: {e}")


class ServerConfig:
    """Global server configuration"""
    
    def __init__(self):
        self.load_from_env()
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        self.debug = os.getenv('MCP_DEBUG', 'false').lower() == 'true'
        self.max_file_size = int(os.getenv('MCP_MAX_FILE_SIZE', '10485760'))  # 10MB default
        self.max_context_size = int(os.getenv('MCP_MAX_CONTEXT_SIZE', '52428800'))  # 50MB default
        
        # Parse allowed extensions (only those that start with a dot)
        exts = os.getenv(
            'MCP_ALLOWED_EXTENSIONS',
            '.py,.js,.ts,.jsx,.tsx,.java,.c,.cpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.r,.m,.h,.hpp,.sh,.bash,.zsh,.fish,.md,.txt,.json,.yaml,.yml,.toml,.xml,.html,.css,.scss,.sass,.less,.sql,.graphql,.proto,.dockerfile,.makefile,.cmake,.gradle,.maven'
        ).split(',')
        self.allowed_extensions = [e.strip().lower() for e in exts if e.strip().startswith('.')]
        
        # Common files without extensions
        self.allowed_basenames = {'dockerfile', 'makefile', 'license', 'readme', 'readme.md'}
        
        # Docker-specific configuration
        self.docker_mode = os.getenv('MCP_DOCKER_MODE', 'false').lower() == 'true'
        self.workspace_dir = os.getenv('MCP_WORKSPACE_DIR', '/workspace')
        
    def is_file_allowed(self, file_path: Path) -> bool:
        """Check if a file is allowed based on extension or basename"""
        try:
            # Check if it has an allowed extension
            if file_path.suffix.lower() in self.allowed_extensions:
                return True
            # Check if it's an allowed suffix-less file
            if file_path.name.lower() in self.allowed_basenames:
                return True
            return False
        except Exception:
            return False
    
    def is_file_size_allowed(self, file_path: Path) -> bool:
        """Check if file size is within limits"""
        try:
            return file_path.stat().st_size <= self.max_file_size
        except:
            return False


# Global server config instance
server_config = ServerConfig()


# -------- Ignore pattern utilities --------

CRITICAL_FILES = {
    "README", "README.md", "package.json", "requirements.txt",
    "pyproject.toml", "setup.py", "Pipfile", "go.mod", "Cargo.toml"
}
PROTECTED_DIRS = {"src", "lib", "app"}

def split_patterns(pipe: str) -> List[str]:
    return [p.strip() for p in (pipe or "").split("|") if p and p.strip()]

def join_patterns(pats: List[str]) -> str:
    # keep order stable-ish but unique
    seen = set()
    out = []
    for p in pats:
        k = p.strip()
        if not k or k.lower() in seen:
            continue
        seen.add(k.lower())
        out.append(k)
    return "|".join(out)

def normalize_patterns(pats: List[str]) -> List[str]:
    # case-insensitive semantics by normalizing for comparisons
    # but keep original casing in storage
    return [p.strip() for p in pats if p and p.strip()]

def validate_ignore_patterns(pats: List[str]) -> Dict[str, Any]:
    """
    Validate ignore patterns against rules:
      1) Don't allow ignoring critical files
      2) Warn on likely source roots (src, lib, app)
      3) Limit overall length
    """
    pats = normalize_patterns(pats)
    errors: List[str] = []
    warnings: List[str] = []

    # Rule 1: block if a pattern equals a critical file name
    lower = {p.lower() for p in pats}
    for c in CRITICAL_FILES:
        if c.lower() in lower:
            errors.append(f"Pattern '{c}' is critical and cannot be ignored.")

    # Rule 2: warn on protected dirs
    for pd in PROTECTED_DIRS:
        if pd.lower() in lower:
            warnings.append(f"Pattern '{pd}' looks like a source directory; consider removing.")

    # Rule 3: limit pattern string length
    final_joined = join_patterns(pats)
    if len(final_joined) > 4000:
        warnings.append("Pattern list is very long; consider trimming to avoid performance issues.")

    return {"errors": errors, "warnings": warnings, "patterns": pats, "joined": final_joined}


def get_default_ignore_patterns() -> List[str]:
    """Get default ignore patterns for different project types"""
    patterns = {
        'python': [
            '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.Python',
            'pip-log.txt', 'pip-delete-this-directory.txt',
            '.venv', 'venv', 'ENV', 'env',
            '.pytest_cache', '.coverage', 'htmlcov',
            '.mypy_cache', '.ruff_cache',
            '*.egg-info', 'dist', 'build',
            '.ipynb_checkpoints'
        ],
        'javascript': [
            'node_modules', 'bower_components',
            '.npm', '.yarn', '.pnp.js',
            'coverage', '.nyc_output',
            '.next', '.nuxt', '.cache',
            'dist', 'build', 'out'
        ],
        'general': [
            '.git', '.svn', '.hg',
            '.DS_Store', 'Thumbs.db',
            '*.log', 'logs',
            '*.sqlite', '*.db',
            '.env', '.env.*',
            '.idea', '.vscode', '.vs',
            '*.swp', '*.swo', '*~',
            '.terraform', '.serverless'
        ]
    }
    
    # Combine all patterns
    all_patterns = []
    for category_patterns in patterns.values():
        all_patterns.extend(category_patterns)
    
    # Remove duplicates and join with pipe
    unique_patterns = list(set(all_patterns))
    return unique_patterns


def detect_project_type(project_path: Path) -> str:
    """Detect the type of project based on files present"""
    indicators = {
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
        'javascript': ['package.json', 'yarn.lock', 'package-lock.json'],
        'rust': ['Cargo.toml'],
        'go': ['go.mod'],
        'java': ['pom.xml', 'build.gradle'],
        'dotnet': ['*.csproj', '*.sln'],
        'ruby': ['Gemfile'],
        'php': ['composer.json']
    }
    
    for lang, files in indicators.items():
        for file_pattern in files:
            if '*' in file_pattern:
                # Handle wildcards
                if list(project_path.glob(file_pattern)):
                    return lang
            else:
                if (project_path / file_pattern).exists():
                    return lang
    
    return 'general'


def suggest_ignore_patterns(project_path: Path) -> str:
    """Suggest ignore patterns based on project type"""
    project_type = detect_project_type(project_path)
    patterns = get_default_ignore_patterns()
    
    # Prioritize patterns for detected project type
    if project_type == 'python':
        python_specific = [
            '__pycache__', '*.pyc', '.venv', 'venv',
            '.pytest_cache', '.mypy_cache'
        ]
        patterns = python_specific + [p for p in patterns if p not in python_specific]
    elif project_type == 'javascript':
        js_specific = [
            'node_modules', '.next', '.nuxt',
            'dist', 'build', 'coverage'
        ]
        patterns = js_specific + [p for p in patterns if p not in js_specific]
    
    # Return top patterns joined with pipe
    return '|'.join(patterns[:15])  # Limit to 15 most relevant patterns


def get_dir_size(path: Path, max_depth: int = 2) -> int:
    """Rough directory size (bytes), shallow to avoid long scans."""
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            # limit depth
            if Path(root).relative_to(path).parts and len(Path(root).relative_to(path).parts) >= max_depth:
                dirs[:] = []  # don't descend further
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total

def analyze_project(project_path: Path) -> Dict[str, Any]:
    """
    Analyze project structure:
      - managers/tools present
      - big directories
      - compiled/binary footprints
      - detected project_type
    """
    project_type = detect_project_type(project_path)
    indicators = {
        "node": (project_path / "package.json").exists(),
        "python": any((project_path / n).exists() for n in ["requirements.txt","pyproject.toml","Pipfile"]),
        "go": (project_path / "go.mod").exists(),
        "rust": (project_path / "Cargo.toml").exists()
    }
    build_tools = [p.name for p in project_path.glob("**/webpack.config.*")]  # quick hint

    big_dirs = []
    for item in project_path.iterdir():
        if item.is_dir() and item.name not in {".git", ".venv", "venv"}:
            sz = get_dir_size(item)
            if sz >= 100_000_000:  # 100MB
                big_dirs.append({"name": item.name, "bytes": sz})

    compiled_globs = ["*.pyc", "*.class", "*.o", "*.so", "*.dll", "*.dylib", "*.test"]
    compiled_present = []
    for pat in compiled_globs:
        if list(project_path.rglob(pat)):
            compiled_present.append(pat)

    return {
        "project_type": project_type,
        "indicators": indicators,
        "build_tools": build_tools,
        "big_dirs": big_dirs,
        "compiled_present": compiled_present,
    }

def suggest_patterns_for_project(project_path: Path) -> Dict[str, List[str]]:
    """Suggest ignore patterns grouped by importance."""
    info = analyze_project(project_path)
    suggestions = {
        "critical": [],
        "recommended": [],
        "optional": []
    }

    if info["indicators"].get("node"):
        suggestions["critical"] += ["node_modules"]
        suggestions["recommended"] += ["dist", "build", ".next", ".nuxt", "coverage", ".cache", "out"]

    if info["indicators"].get("python"):
        suggestions["critical"] += [".venv", "venv", "__pycache__"]
        suggestions["recommended"] += ["*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", "*.egg-info", "build", "dist"]

    if info["indicators"].get("go"):
        suggestions["critical"] += ["vendor", "bin"]
        suggestions["recommended"] += ["*.test"]

    if info["indicators"].get("rust"):
        suggestions["recommended"] += ["target"]

    # Always add general junk
    general = [".git", ".DS_Store", "Thumbs.db", "*.log", "logs", ".idea", ".vscode", ".nyc_output", ".terraform", ".serverless"]
    for g in general:
        if g not in suggestions["critical"] and g not in suggestions["recommended"]:
            suggestions["recommended"].append(g)

    # Very large top-level dirs => critical
    for d in info["big_dirs"]:
        if d["name"] not in suggestions["critical"]:
            suggestions["critical"].append(d["name"])

    # De-duplicate and normalize
    for k in list(suggestions.keys()):
        suggestions[k] = normalize_patterns(list(dict.fromkeys(suggestions[k])))

    return suggestions


# Configuration templates for common scenarios
CONFIG_TEMPLATES = {
    'debug': {
        'tree_ignore': suggest_ignore_patterns(Path.cwd()),
        'output_dir': 'context_reports/debug',
        'default_context_dumps': [
            {'file': '.llm_prep_notes/error_logs.md', 'title': 'Error Logs'},
            {'file': '.llm_prep_notes/debug_notes.md', 'title': 'Debug Analysis'}
        ]
    },
    'feature': {
        'tree_ignore': suggest_ignore_patterns(Path.cwd()),
        'output_dir': 'context_reports/features',
        'default_context_dumps': [
            {'file': 'docs/requirements.md', 'title': 'Requirements'},
            {'file': 'docs/architecture.md', 'title': 'Architecture'}
        ]
    },
    'review': {
        'tree_ignore': suggest_ignore_patterns(Path.cwd()),
        'output_dir': 'context_reports/reviews',
        'default_context_dumps': [
            {'file': 'CHANGELOG.md', 'title': 'Recent Changes'},
            {'file': '.llm_prep_notes/review_notes.md', 'title': 'Review Notes'}
        ]
    }
}


def apply_config_template(project_path: Path, template_name: str) -> ProjectConfig:
    """Apply a configuration template to a project"""
    if template_name not in CONFIG_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    
    template = CONFIG_TEMPLATES[template_name]
    config = ProjectConfig(**template)
    
    # Adjust paths for project
    config.tree_ignore = suggest_ignore_patterns(project_path)
    
    return config
