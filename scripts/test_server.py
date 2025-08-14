#!/usr/bin/env python3
"""
Test script for LLM Context Prep MCP Server
Tests all major functionality
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

# For testing without MCP client, we'll simulate the calls
USE_MCP_CLIENT = False

try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    USE_MCP_CLIENT = True
except ImportError:
    print("MCP client not available, using direct function calls")

# Import the server modules directly for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from mcp_server import LLMPrepMCPServer


class TestRunner:
    """Test runner for MCP server"""
    
    def __init__(self):
        self.server = LLMPrepMCPServer()
        self.test_dir = None
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    async def setup(self):
        """Set up test environment"""
        # Create temporary test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="llm_test_"))
        print(f"Test directory: {self.test_dir}")
        
        # Create test files
        (self.test_dir / "main.py").write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")
        
        (self.test_dir / "utils.py").write_text("""
def helper_function():
    return "Helper"
""")
        
        (self.test_dir / "README.md").write_text("""
# Test Project
This is a test project for MCP server testing.
""")
        
        # Create subdirectory with files
        (self.test_dir / "src").mkdir()
        (self.test_dir / "src" / "module.py").write_text("""
class TestClass:
    pass
""")
    
    async def teardown(self):
        """Clean up test environment"""
        if self.test_dir and self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir)
            print(f"Cleaned up test directory")
    
    async def test_create_debug_notes(self):
        """Test creating debug notes"""
        print("\n📝 Testing create_debug_notes...")
        
        try:
            result = await self.server.create_debug_notes(
                project_path=str(self.test_dir),
                filename="test_debug.md",
                content="""
# Debug Notes

## Error
Something went wrong

## Attempted Solutions
- Tried restarting
- Checked logs
"""
            )
            
            # Check if file was created
            notes_file = self.test_dir / ".llm_prep_notes" / "test_debug.md"
            assert notes_file.exists(), "Debug notes file not created"
            assert "Debug Notes" in notes_file.read_text(), "Content not written correctly"
            
            print(f"   ✅ Created debug notes: {notes_file}")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def test_set_project_config(self):
        """Test setting project configuration"""
        print("\n⚙️  Testing set_project_config...")
        
        try:
            result = await self.server.set_project_config(
                project_path=str(self.test_dir),
                tree_ignore="*.pyc|__pycache__|.git",
                default_output_dir="context_output"
            )
            
            # Check if config was created
            config_file = self.test_dir / ".llm_prep_config.json"
            assert config_file.exists(), "Config file not created"
            
            config = json.loads(config_file.read_text())
            assert config["tree_ignore"] == "*.pyc|__pycache__|.git"
            assert config["output_dir"] == "context_output"
            
            print(f"   ✅ Config saved: {config_file}")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def test_prepare_context(self):
        """Test preparing context document"""
        print("\n📄 Testing prepare_context...")
        
        try:
            # First create a debug note
            await self.server.create_debug_notes(
                project_path=str(self.test_dir),
                filename="context_test.md",
                content="Test context dump content"
            )
            
            # Prepare context
            result = await self.server.prepare_context(
                project_path=str(self.test_dir),
                files=[
                    {"path": "main.py", "note": "Main entry point"},
                    {"path": "utils.py", "note": "Utility functions"}
                ],
                context_dumps=[
                    {"file": ".llm_prep_notes/context_test.md", "title": "Test Context"}
                ],
                general_notes=["This is a test", "Another note"],
                output_name="test_context.md"
            )
            
            # Check if context was created
            context_file = self.test_dir / "context_reports" / "test_context.md"
            assert context_file.exists(), "Context file not created"
            
            content = context_file.read_text()
            assert "main.py" in content, "File not included"
            assert "Main entry point" in content, "File note not included"
            assert "Test context dump content" in content, "Context dump not included"
            assert "This is a test" in content, "General note not included"
            
            print(f"   ✅ Context created: {context_file}")
            print(f"   📊 Size: {len(content):,} characters")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def test_list_recent_contexts(self):
        """Test listing recent contexts"""
        print("\n📚 Testing list_recent_contexts...")
        
        try:
            result = await self.server.list_recent_contexts(
                project_path=str(self.test_dir),
                limit=5
            )
            
            assert "Recent Context Documents" in result or "No recent" in result
            print(f"   ✅ Listed contexts successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def test_clean_temp_notes(self):
        """Test cleaning temporary notes"""
        print("\n🧹 Testing clean_temp_notes...")
        
        try:
            # Create an old note file
            notes_dir = self.test_dir / ".llm_prep_notes"
            notes_dir.mkdir(exist_ok=True)
            old_file = notes_dir / "old_note.md"
            old_file.write_text("Old content")
            
            # Make it appear old
            import time
            old_time = time.time() - (8 * 86400)  # 8 days ago
            import os
            os.utime(old_file, (old_time, old_time))
            
            result = await self.server.clean_temp_notes(
                project_path=str(self.test_dir),
                older_than_days=7
            )
            
            assert not old_file.exists(), "Old file not deleted"
            print(f"   ✅ Cleaned old notes")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def test_mcp_tools_list(self):
        """Test MCP tools listing"""
        print("\n🔧 Testing MCP tools list...")
        
        try:
            tools = await self.server.server.list_tools()
            tool_names = [tool.name for tool in tools]
            
            expected_tools = [
                "prepare_context",
                "create_debug_notes",
                "set_project_config",
                "list_recent_contexts",
                "clean_temp_notes"
            ]
            
            for expected in expected_tools:
                assert expected in tool_names, f"Tool {expected} not found"
            
            print(f"   ✅ All {len(tools)} tools available")
            for tool in tools:
                print(f"      - {tool.name}: {tool.description[:50]}...")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def test_mcp_prompts(self):
        """Test MCP prompts"""
        print("\n💬 Testing MCP prompts...")
        
        try:
            prompts = await self.server.server.list_prompts()
            prompt_names = [p["name"] for p in prompts]
            
            expected_prompts = ["debug_workflow", "feature_implementation"]
            
            for expected in expected_prompts:
                assert expected in prompt_names, f"Prompt {expected} not found"
            
            # Test getting a specific prompt
            debug_prompt = await self.server.server.get_prompt(
                "debug_workflow",
                {"issue_description": "Test issue"}
            )
            
            assert "messages" in debug_prompt
            assert len(debug_prompt["messages"]) > 0
            
            print(f"   ✅ All prompts available")
            for prompt in prompts:
                print(f"      - {prompt['name']}: {prompt['description'][:50]}...")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("🧪 LLM Context Prep MCP Server - Test Suite")
        print("="*60)
        
        await self.setup()
        
        tests = [
            self.test_create_debug_notes,
            self.test_set_project_config,
            self.test_prepare_context,
            self.test_list_recent_contexts,
            self.test_clean_temp_notes,
            self.test_mcp_tools_list,
            self.test_mcp_prompts
        ]
        
        for test in tests:
            if await test():
                self.passed += 1
            else:
                self.failed += 1
        
        await self.teardown()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 Test Results")
        print("="*60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Total: {self.passed + self.failed}")
        
        if self.failed == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {self.failed} tests failed")
        
        return self.failed == 0


async def test_with_mcp_client():
    """Test using actual MCP client (if available)"""
    if not USE_MCP_CLIENT:
        print("MCP client not available, skipping client tests")
        return
    
    print("\n" + "="*60)
    print("🔌 Testing with MCP Client")
    print("="*60)
    
    # This would connect to the actual running MCP server
    # For now, we'll skip this as it requires the server to be running
    print("Skipping MCP client tests (requires running server)")


async def main():
    """Main test function"""
    # Run direct tests
    runner = TestRunner()
    success = await runner.run_all_tests()
    
    # Run MCP client tests if available
    await test_with_mcp_client()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
