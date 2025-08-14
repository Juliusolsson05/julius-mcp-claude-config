#!/usr/bin/env python3
"""
Configuration management for LLM Context Prep MCP Server
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class ProjectConfig:
    """Configuration for a specific project"""
    tree_ignore: str = "bin|lib|*.log|logs|__pycache__|*.csv|*.pyc|.git|.env|*.db|node_modules|.venv|venv"
    output_dir: str = "context_reports"
    default_context_dumps: List[Dict[str, str]] = field(default_factory=list)
    recent_contexts: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectConfig':
        """Create from dictionary"""
        return cls(
            tree_ignore=data.get('tree_ignore', cls.tree_ignore.__default__),
            output_dir=data.get('output_dir', cls.output_dir.__default__),
            default_context_dumps=data.get('default_context_dumps', []),
            recent_contexts=data.get('recent_contexts', [])
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
        self.allowed_extensions = os.getenv(
            'MCP_ALLOWED_EXTENSIONS',
            '.py,.js,.ts,.jsx,.tsx,.java,.c,.cpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.r,.m,.h,.hpp,.sh,.bash,.zsh,.fish,.md,.txt,.json,.yaml,.yml,.toml,.xml,.html,.css,.scss,.sass,.less,.sql,.graphql,.proto,.dockerfile,.makefile,.cmake,.gradle,.maven'
        ).split(',')
        
        # Docker-specific configuration
        self.docker_mode = os.getenv('MCP_DOCKER_MODE', 'false').lower() == 'true'
        self.workspace_dir = os.getenv('MCP_WORKSPACE_DIR', '/workspace')
        
    def is_file_allowed(self, file_path: Path) -> bool:
        """Check if a file is allowed based on extension"""
        return file_path.suffix.lower() in self.allowed_extensions
    
    def is_file_size_allowed(self, file_path: Path) -> bool:
        """Check if file size is within limits"""
        try:
            return file_path.stat().st_size <= self.max_file_size
        except:
            return False


# Global server config instance
server_config = ServerConfig()


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
