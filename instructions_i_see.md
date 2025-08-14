# Instructions and Information I See as Claude (AI Agent) Using the LLM-Prep MCP Server

## What I See When Starting Fresh

When I encounter the `llm-prep` MCP server in a new conversation, here's exactly what information is available to me:

## 1. Available MCP Tools

### `mcp__llm-prep__prepare_context`
**What it tells me**: "Prepare comprehensive LLM context document from files and notes"

**Parameters I see**:
- `project_path` (required) - Path to the project root directory
- `files` (optional) - List of files to include with optional notes
- `context_dumps` (optional) - List of markdown files to include as context dumps  
- `general_notes` (optional) - Quick context notes
- `output_name` (optional) - Output filename (saved to context_reports/)
- `tree_ignore` (optional) - Patterns to ignore in tree generation

**My understanding**: This is the main tool for creating a comprehensive document that combines multiple files, notes, and context into one markdown file for LLM consumption.

### `mcp__llm-prep__create_debug_notes`
**What it tells me**: "Create markdown notes file for later use as context dump"

**Parameters I see**:
- `project_path` (required) - Path to the project root
- `filename` (required) - Name of the markdown file to create
- `content` (required) - Markdown content to save
- `subfolder` (optional, default: ".llm_prep_notes") - Optional subfolder

**My understanding**: I should use this to save debug information, error logs, or analysis notes that can be included in context documents later.

### `mcp__llm-prep__set_project_config`
**What it tells me**: "Configure project-specific settings for context preparation"

**Parameters I see**:
- `project_path` (required) - Path to the project root
- `tree_ignore` (optional) - Patterns to ignore in tree generation
- `default_output_dir` (optional) - Default directory for context reports
- `default_context_dumps` (optional) - Default context dumps to include

**My understanding**: This configures defaults for a project, so I don't need to specify the same settings repeatedly.

### `mcp__llm-prep__list_recent_contexts`
**What it tells me**: "List recently generated context documents for a project"

**Parameters I see**:
- `project_path` (required) - Path to the project root
- `limit` (optional, default: 10) - Maximum number of recent contexts to return

**My understanding**: Shows me what context documents have been created recently, useful for tracking work.

### `mcp__llm-prep__clean_temp_notes`
**What it tells me**: "Clean up temporary note files in .llm_prep_notes"

**Parameters I see**:
- `project_path` (required) - Path to the project root
- `older_than_days` (optional, default: 7) - Delete files older than this many days

**My understanding**: Housekeeping tool to remove old temporary notes.

### `mcp__llm-prep__get_tree_ignore`
**What it tells me**: "Get current tree ignore patterns and suggestions"

**Parameters I see**:
- `project_path` (required) - Path to the project root

**My understanding**: Shows current ignore patterns and suggests what else could be ignored based on project type.

### `mcp__llm-prep__update_tree_ignore`
**What it tells me**: "Update tree ignore patterns with intelligent suggestions & history"

**Parameters I see**:
- `project_path` (required) - Path to the project root
- `action` (optional, default: "add") - How to apply changes: "set", "add", "remove", "auto"
- `patterns` (optional) - Patterns for set/add/remove
- `auto_detect` (optional, default: false) - If true, analyze project to select patterns
- `reason` (optional) - Why this change is made (stored in history)

**My understanding**: Manages what files/folders to exclude from context. The "auto" action seems powerful for automatic configuration.

### `mcp__llm-prep__analyze_project_structure`
**What it tells me**: "Analyze project and suggest optimal ignore patterns"

**Parameters I see**:
- `project_path` (required) - Path to the project root

**My understanding**: Analyzes the project to understand its type and structure, suggesting what should be ignored.

## 2. Inferred Workflow from Tool Descriptions

Based on the tool descriptions alone, I understand the workflow should be:

1. **Initial Setup** (when starting with a new project):
   - Use `analyze_project_structure` to understand the project
   - Use `get_tree_ignore` to see current patterns
   - Use `update_tree_ignore` with `action="auto"` to auto-configure

2. **During Debugging**:
   - Use `create_debug_notes` to save error logs and analysis
   - Collect relevant files
   - Use `prepare_context` to combine everything

3. **For Feature Development**:
   - Create requirement notes with `create_debug_notes`
   - Identify relevant files
   - Generate context with `prepare_context`

## 3. What's NOT Clear from Tool Descriptions Alone

### Missing Context:
- **File path format**: Should paths be absolute or relative?
- **Pattern syntax**: What format for tree_ignore patterns? (Glob? Regex? Pipe-separated?)
- **Output location**: Where exactly do context documents get saved?
- **File size limits**: Are there any limits on file sizes or context document size?
- **Best practices**: When to use context dumps vs inline files?

### Ambiguous Behaviors:
- What happens if output_name is not specified in `prepare_context`?
- How does the "auto" action in `update_tree_ignore` determine what to ignore?
- What's the difference between adding files directly vs as context dumps?
- How are duplicate patterns handled in tree_ignore?

### Implicit Knowledge Needed:
- The two-stage workflow (Claude Code → MCP → Claude.ai) isn't obvious from tools alone
- The purpose of separating debug notes into `.llm_prep_notes/` isn't clear
- The relationship between project config and individual tool calls

## 4. What Would Help Me as an AI Agent

### Clearer Tool Descriptions:
Instead of: "Prepare comprehensive LLM context document from files and notes"
Better: "Combine multiple source files and markdown notes into a single context document for uploading to LLM web interfaces. Files are included with full content, while context_dumps are markdown files that get appended as sections."

### Parameter Clarifications:
Instead of: `tree_ignore` - "Patterns to ignore in tree generation"
Better: `tree_ignore` - "Pipe-separated glob patterns to exclude from project tree (e.g., 'node_modules|*.pyc|.git')"

### Workflow Hints in Descriptions:
Add to tool descriptions:
- "Typically used after create_debug_notes to combine files and notes"
- "Run analyze_project_structure first to get suggestions"
- "Use action='auto' for automatic configuration based on project type"

### Success/Error Examples:
What I'd like to see in responses:
- "✅ Context document saved to: /path/to/context_reports/debug_20250814.md (1.2MB)"
- "❌ Error: Pattern 'README.md' is critical and cannot be ignored"

## 5. The Actual Workflow I've Learned

Through experience (not from descriptions), I now know:

1. **Project Setup Flow**:
   ```
   analyze_project_structure → get_tree_ignore → update_tree_ignore(action="auto")
   ```

2. **Debug Context Flow**:
   ```
   create_debug_notes (save errors) → prepare_context (combine all) → upload to Claude.ai
   ```

3. **Hidden Features**:
   - History tracking in tree_ignore
   - Project type detection (Python, JavaScript, etc.)
   - Critical file protection (won't ignore README, package.json, etc.)
   - Large directory detection (>100MB)

## 6. Suggestions for Improvement

### Tool Naming:
- Consider prefixing tools with their category: `config_update_tree_ignore`, `notes_create_debug`, `context_prepare`

### Response Format:
- Standardize emoji usage: ✅ for success, ❌ for errors, ⚠️ for warnings
- Always include file paths and sizes in responses
- Show what was actually done, not just "success"

### Documentation in Tool Descriptions:
- Add example usage in each tool's description
- Specify format requirements (pipe-separated, absolute paths, etc.)
- Mention related tools ("Use after analyze_project_structure")

### Prompts/Templates:
- The MCP server could provide prompt templates for common workflows
- These would guide AI agents through multi-step processes

## Conclusion

As an AI agent, I can figure out how to use these tools through experimentation, but clearer descriptions, parameter documentation, and workflow hints would make the tools much more immediately useful. The current descriptions assume knowledge about the broader context preparation workflow that isn't explicitly stated in the tool interfaces.