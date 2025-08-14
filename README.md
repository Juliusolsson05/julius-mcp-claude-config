# LLM Context Preparation MCP Server

A Model Context Protocol (MCP) server that helps prepare comprehensive context documents for Large Language Models when dealing with complex codebases that exceed token limits.

## 🎯 Problem This Solves

When debugging complex issues or implementing features across multiple files, AI coding assistants like Claude Code often hit token limits. This MCP server enables a two-stage workflow:

1. **Claude Code** prepares detailed notes and identifies relevant files
2. **MCP Server** generates a comprehensive context document
3. **Upload** the document to Claude.ai for deep analysis with higher token limits

## 🚀 Quick Start with Docker

### Option 1: Run Pre-built Image (Fastest)

```bash
# Pull and run the image
docker run -it --rm \
  -v $(pwd):/workspace \
  llm-context-prep-mcp:latest

# Or use docker-compose
docker-compose -f docker/docker-compose.yml up
```

### Option 2: Build from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-context-prep-mcp.git
cd llm-context-prep-mcp

# Build the Docker image
docker build -f docker/Dockerfile -t llm-context-prep-mcp:latest .

# Run the container
docker run -it --rm \
  -v $(pwd):/workspace \
  llm-context-prep-mcp:latest
```

## 🔧 Installation for Claude Code

### 1. Add the MCP Server

```bash
# Using Docker (recommended)
claude mcp add llm-prep --env WORKSPACE_DIR=$(pwd) -- \
  docker run -i --rm -v $(pwd):/workspace llm-context-prep-mcp:latest

# Or using local Python
claude mcp add llm-prep -- python /path/to/llm-context-prep-mcp/src/mcp_server.py
```

### 2. Verify Installation

In Claude Code:
```
/mcp
```

You should see `llm-prep` in the list of connected servers.

## 📖 How to Use

### Available MCP Tools

1. **`prepare_context`** - Generate comprehensive context documents
2. **`create_debug_notes`** - Create markdown notes for context dumps
3. **`set_project_config`** - Configure project-specific settings
4. **`list_recent_contexts`** - View recently generated contexts
5. **`clean_temp_notes`** - Clean up temporary note files

### Workflow Example: Debugging an Issue

In Claude Code:

```
# Step 1: Use the debug workflow prompt
/mcp__llm_prep__debug_workflow "Celery tasks not being discovered"

# Step 2: Claude Code will guide you through:
# - Creating debug notes with error logs
# - Identifying relevant files
# - Generating a comprehensive context document

# Step 3: Find your context document in context_reports/
# Upload to Claude.ai for deep analysis
```

### Manual Workflow

```python
# 1. Create debug notes
await create_debug_notes(
    project_path="/workspace/myproject",
    filename="celery_debug.md",
    content="""
    # Celery Debug Session
    
    ## Error Logs
    [2025-01-15 10:30:00] ERROR: Task 'app.tasks.send_email' not found
    ...
    
    ## What We've Tried
    - Restarted workers
    - Checked Redis connection
    """
)

# 2. Prepare context document
await prepare_context(
    project_path="/workspace/myproject",
    files=[
        {"path": "celery_app.py", "note": "Main configuration"},
        {"path": "tasks.py", "note": "Task definitions"}
    ],
    context_dumps=[
        {"file": ".llm_prep_notes/celery_debug.md", "title": "Debug Session"}
    ],
    output_name="celery_debug_context.md"
)
```

## 🗂️ Project Structure

```
your_project/
├── .llm_prep_config.json    # Project configuration
├── .llm_prep_notes/         # Temporary debug notes
│   ├── debug_analysis.md
│   └── error_logs.md
├── context_reports/         # Generated context documents
│   ├── 2025-01-15_celery_debug.md
│   └── 2025-01-16_feature_auth.md
└── [your project files]
```

## ⚙️ Configuration

### Project Configuration (`.llm_prep_config.json`)

```json
{
  "tree_ignore": "*.pyc|__pycache__|node_modules|.git",
  "output_dir": "context_reports",
  "default_context_dumps": [
    {"file": "docs/architecture.md", "title": "System Architecture"}
  ]
}
```

### Environment Variables

```bash
# Docker/Server Configuration
MCP_DEBUG=false                    # Enable debug logging
MCP_MAX_FILE_SIZE=10485760        # Max file size (10MB)
MCP_MAX_CONTEXT_SIZE=52428800     # Max context size (50MB)
MCP_WORKSPACE_DIR=/workspace       # Workspace directory in Docker

# File Extensions
MCP_ALLOWED_EXTENSIONS=.py,.js,.ts,.md,.txt,.json,.yaml
```

## 🎯 MCP Prompts

The server provides intelligent prompts for common workflows:

- `/mcp__llm_prep__debug_workflow` - Complete debugging workflow
- `/mcp__llm_prep__feature_implementation` - Feature development context
- `/mcp__llm_prep__code_review` - Code review preparation
- `/mcp__llm_prep__performance_analysis` - Performance optimization

## 🐳 Docker Details

### Building the Image

```bash
# Standard build
docker build -f docker/Dockerfile -t llm-context-prep-mcp:latest .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile -t llm-context-prep-mcp:latest .
```

### Running with Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  llm-prep:
    image: llm-context-prep-mcp:latest
    stdin_open: true
    tty: true
    volumes:
      - ${PWD}:/workspace
    environment:
      - MCP_DEBUG=false
```

### Security Considerations

- Runs as non-root user `mcp`
- Read-only root filesystem (except `/workspace` and `/tmp`)
- No new privileges
- Resource limits enforced

## 🧪 Testing

### Test the MCP Server

```python
# scripts/test_server.py
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async def test():
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")
            
            # Test create_debug_notes
            result = await session.call_tool(
                "create_debug_notes",
                {
                    "project_path": "/workspace",
                    "filename": "test.md",
                    "content": "Test content"
                }
            )
            print(f"Result: {result}")

asyncio.run(test())
```

## 📊 Best Practices

1. **Large Error Logs**: Always use `create_debug_notes` for logs over 100 lines
2. **File Organization**: Keep debug notes in `.llm_prep_notes/`, contexts in `context_reports/`
3. **Descriptive Notes**: Add clear notes to each file explaining its relevance
4. **Context Size**: Keep documents under 2MB for optimal performance
5. **Regular Cleanup**: Use `clean_temp_notes` to remove old temporary files

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🔗 Links

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## ❓ FAQ

**Q: How is this different from just copying files to Claude?**
A: This tool creates structured, comprehensive contexts with project trees, line numbers, and organized sections optimized for LLM consumption.

**Q: Can I use this without Docker?**
A: Yes, install Python 3.11+ and run `pip install -r requirements.txt`, then use the local Python command.

**Q: How do I handle secrets/sensitive data?**
A: Add sensitive files to `tree_ignore` patterns and never include them in context documents.

**Q: What's the maximum context size?**
A: Default is 50MB, but Claude.ai typically handles 100K-200K tokens well (roughly 400K-800K characters).

## 🐛 Troubleshooting

### "Connection closed" error
- Ensure Docker is running
- Check that the image exists: `docker images | grep llm-context-prep`
- Verify volume mounts are correct

### Files not found
- Ensure you're using relative paths from project root
- Check that files exist in the mounted workspace
- Verify file permissions

### Context too large
- Use `tree_ignore` to exclude unnecessary directories
- Split into multiple focused contexts
- Remove large binary files or datasets

