#!/usr/bin/env python3
"""
Test script for LLM Context Prep MCP Server using FastMCP
Tests all major functionality with the new FastMCP implementation
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import FastMCP tool functions and models
from mcp_server_fastmcp import (
    prepare_context, create_debug_notes, set_project_config,
    list_recent_contexts, clean_temp_notes,
    PrepareContextInput, CreateDebugNotesInput, SetProjectConfigInput,
    ListRecentContextsInput, CleanTempNotesInput
)


class TestRunner:
    """Test runner for FastMCP server"""
    
    def __init__(self):
        self.test_dir: Path | None = None
        self.passed = 0
        self.failed = 0
    
    async def setup(self):
        """Set up test environment"""
        # Create temporary test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="llm_test_"))
        print(f"Test directory: {self.test_dir}")
        
        # Create test files
        (self.test_dir / "main.py").write_text('print("hello")\n')
        (self.test_dir / "utils.py").write_text('def helper():\n    return "ok"\n')
        (self.test_dir / "README.md").write_text("# Test Project\n")
        
        # Create src directory with module
        (self.test_dir / "src").mkdir()
        (self.test_dir / "src" / "module.py").write_text("class X:\n    pass\n")
    
    async def teardown(self):
        """Clean up test environment"""
        if self.test_dir and self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir)
            print("Cleaned up test directory")
    
    async def t_create_debug_notes(self):
        """Test creating debug notes"""
        try:
            res = await create_debug_notes(CreateDebugNotesInput(
                project_path=str(self.test_dir),
                filename="test_debug.md",
                content="# Debug\nTest content"
            ))
            notes_file = self.test_dir / ".llm_prep_notes" / "test_debug.md"
            assert notes_file.exists(), "Debug notes file was not created"
            print("   ✅ create_debug_notes")
            return True
        except Exception as e:
            print(f"   ❌ create_debug_notes: {e}")
            return False
    
    async def t_set_project_config(self):
        """Test setting project configuration"""
        try:
            res = await set_project_config(SetProjectConfigInput(
                project_path=str(self.test_dir),
                tree_ignore="*.pyc|__pycache__|.git",
                default_output_dir="context_output"
            ))
            config_file = self.test_dir / ".llm_prep_config.json"
            assert config_file.exists(), "Config file was not created"
            cfg = json.loads(config_file.read_text())
            assert cfg["output_dir"] == "context_output", "Output dir not set correctly"
            print("   ✅ set_project_config")
            return True
        except Exception as e:
            print(f"   ❌ set_project_config: {e}")
            return False
    
    async def t_prepare_context(self):
        """Test preparing context document"""
        try:
            # Create a debug note first
            _ = await create_debug_notes(CreateDebugNotesInput(
                project_path=str(self.test_dir),
                filename="context_test.md",
                content="Context dump test"
            ))
            
            res = await prepare_context(PrepareContextInput(
                project_path=str(self.test_dir),
                files=[
                    {"path": "main.py", "note": "entry point"},
                    {"path": "utils.py", "note": "helper functions"}
                ],
                context_dumps=[{"file": ".llm_prep_notes/context_test.md", "title": "Test Dump"}],
                general_notes=["note A", "note B"],
                output_name="test_context.md"
            ))
            
            # Check for context file in configured or default output directory
            ctx = self.test_dir / "context_output" / "test_context.md"
            if not ctx.exists():
                ctx = self.test_dir / "context_reports" / "test_context.md"
            assert ctx.exists(), "Context file was not created"
            print("   ✅ prepare_context")
            return True
        except Exception as e:
            print(f"   ❌ prepare_context: {e}")
            return False
    
    async def t_list_recent_contexts(self):
        """Test listing recent contexts"""
        try:
            res = await list_recent_contexts(ListRecentContextsInput(
                project_path=str(self.test_dir),
                limit=5
            ))
            assert "Context" in res or "No recent" in res, "Unexpected response"
            print("   ✅ list_recent_contexts")
            return True
        except Exception as e:
            print(f"   ❌ list_recent_contexts: {e}")
            return False
    
    async def t_clean_temp_notes(self):
        """Test cleaning temporary notes"""
        try:
            # Create an old note file
            notes_dir = self.test_dir / ".llm_prep_notes"
            notes_dir.mkdir(exist_ok=True)
            old_file = notes_dir / "old.md"
            old_file.write_text("old content")
            
            # Set modification time to 9 days ago
            import os, time
            old_time = time.time() - 9*86400
            os.utime(old_file, (old_time, old_time))
            
            res = await clean_temp_notes(CleanTempNotesInput(
                project_path=str(self.test_dir),
                older_than_days=7
            ))
            
            assert not old_file.exists(), "Old file was not deleted"
            print("   ✅ clean_temp_notes")
            return True
        except Exception as e:
            print(f"   ❌ clean_temp_notes: {e}")
            return False
    
    async def t_tree_ignore_tools(self):
        """Test tree ignore tools"""
        try:
            # Import the new tools
            from mcp_server_fastmcp import (
                get_tree_ignore, update_tree_ignore, analyze_project_structure,
                GetTreeIgnoreInput, UpdateTreeIgnoreInput, AnalyzeProjectInput
            )
            
            # Test analyze
            res = await analyze_project_structure(AnalyzeProjectInput(
                project_path=str(self.test_dir)
            ))
            assert "Project:" in res, "Analyze didn't return project info"
            
            # Test add patterns
            res = await update_tree_ignore(UpdateTreeIgnoreInput(
                project_path=str(self.test_dir),
                action="add",
                patterns=["__pycache__", "*.pyc", "dist"]
            ))
            assert "✅" in res, "Add patterns failed"
            
            # Test get current
            res = await get_tree_ignore(GetTreeIgnoreInput(
                project_path=str(self.test_dir)
            ))
            assert "__pycache__" in res, "Pattern not found after adding"
            
            # Test remove
            res = await update_tree_ignore(UpdateTreeIgnoreInput(
                project_path=str(self.test_dir),
                action="remove",
                patterns=["dist"]
            ))
            assert "✅" in res, "Remove pattern failed"
            
            # Test auto-configure
            res = await update_tree_ignore(UpdateTreeIgnoreInput(
                project_path=str(self.test_dir),
                action="auto",
                auto_detect=True,
                reason="Auto test"
            ))
            assert "✅" in res, "Auto-configure failed"
            
            print("   ✅ tree ignore tools")
            return True
        except Exception as e:
            print(f"   ❌ tree ignore tools: {e}")
            return False
    
    async def run_all(self):
        """Run all tests"""
        await self.setup()
        
        tests = [
            self.t_create_debug_notes,
            self.t_set_project_config,
            self.t_tree_ignore_tools,
            self.t_prepare_context,
            self.t_list_recent_contexts,
            self.t_clean_temp_notes
        ]
        
        print("\nRunning tests...")
        print("=" * 50)
        
        for test in tests:
            success = await test()
            if success:
                self.passed += 1
            else:
                self.failed += 1
        
        await self.teardown()
        
        print("=" * 50)
        print(f"\nResults: Passed={self.passed}, Failed={self.failed}")
        return self.failed == 0


async def main():
    """Main entry point"""
    runner = TestRunner()
    success = await runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())