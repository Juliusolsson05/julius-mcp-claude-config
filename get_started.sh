#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Header
echo ""
echo "=================================================="
echo "🚀 LLM Context Prep MCP Server - Quick Start"
echo "=================================================="
echo ""

# Step 1: Check for Python
print_info "Checking Python installation..."

# Try to find Python 3
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # Check if 'python' is Python 3
    PYTHON_VERSION=$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
    if [ "$MAJOR_VERSION" -ge "3" ]; then
        PYTHON_CMD="python"
    else
        print_error "Python 3 is required but only Python 2 was found"
        print_info "Please install Python 3.8 or higher from https://www.python.org"
        exit 1
    fi
else
    print_error "Python is not installed"
    print_info "Please install Python 3.8 or higher from https://www.python.org"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

print_success "Found Python $PYTHON_VERSION at $(which $PYTHON_CMD)"

if [ "$MAJOR" -lt "3" ] || ([ "$MAJOR" -eq "3" ] && [ "$MINOR" -lt "8" ]); then
    print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Step 2: Create virtual environment
print_info "Setting up virtual environment..."

VENV_DIR="venv"

# Remove old venv if exists
if [ -d "$VENV_DIR" ]; then
    print_warning "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment
$PYTHON_CMD -m venv "$VENV_DIR"

if [ $? -ne 0 ]; then
    print_error "Failed to create virtual environment"
    print_info "Trying to install venv module..."
    
    # Try to install venv if not available
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "On macOS, you might need to install python3-venv via Homebrew"
        print_info "Run: brew install python3"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_info "On Linux, you might need to install python3-venv"
        print_info "Run: sudo apt-get install python3-venv (Ubuntu/Debian)"
        print_info "Or: sudo yum install python3-venv (RedHat/CentOS)"
    fi
    exit 1
fi

print_success "Virtual environment created"

# Step 3: Activate virtual environment
print_info "Activating virtual environment..."

# Detect OS and activate accordingly
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
    PIP_CMD="$VENV_DIR/Scripts/pip"
    PYTHON_VENV="$VENV_DIR/Scripts/python"
else
    # Unix-like (macOS, Linux)
    ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
    PIP_CMD="$VENV_DIR/bin/pip"
    PYTHON_VENV="$VENV_DIR/bin/python"
fi

# Step 4: Upgrade pip
print_info "Upgrading pip..."
$PYTHON_VENV -m pip install --upgrade pip --quiet

if [ $? -ne 0 ]; then
    print_warning "Could not upgrade pip, continuing with current version"
fi

# Step 5: Install dependencies
print_info "Installing dependencies..."

$PIP_CMD install -r requirements.txt

if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    print_info "Trying to install core dependencies one by one..."
    
    # Try installing core dependencies individually
    $PIP_CMD install mcp
    $PIP_CMD install fastapi uvicorn starlette sse-starlette
    
    if [ $? -ne 0 ]; then
        print_error "Could not install core dependencies"
        exit 1
    fi
fi

print_success "Dependencies installed"

# Step 6: Create helper scripts
print_info "Creating helper scripts..."

# Create run script for SSE server
cat > run_sse_server.sh << 'EOF'
#!/bin/bash
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Load port from .env file if it exists
if [ -f .env ]; then
    export $(grep -E '^MCP_SERVER_PORT=' .env | xargs)
fi

# Use port from env or default to 8847
PORT=${MCP_SERVER_PORT:-8847}

echo "🚀 Starting LLM Context Prep MCP Server on localhost:$PORT"
echo "=================================================="
echo ""
echo "Server is running at: http://localhost:$PORT/sse"
echo ""
echo "To connect Claude Code, run in another terminal:"
echo "  claude mcp add --transport sse llm-prep http://localhost:$PORT/sse"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================================="
echo ""

python src/mcp_server_fastmcp.py --transport sse --port $PORT
EOF

chmod +x run_sse_server.sh

# Create run script for stdio server
cat > run_stdio_server.sh << 'EOF'
#!/bin/bash
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

echo "🚀 Starting LLM Context Prep MCP Server (stdio mode)"
echo "=================================================="
echo ""
echo "This is running in stdio mode for testing."
echo "For Claude Code integration, use run_sse_server.sh instead"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

python src/mcp_server_fastmcp.py --transport stdio
EOF

chmod +x run_stdio_server.sh

# Create add to Claude script
cat > add_to_claude.sh << 'EOF'
#!/bin/bash

# Load port from .env file if it exists
if [ -f .env ]; then
    export $(grep -E '^MCP_SERVER_PORT=' .env | xargs)
fi

# Use port from env or default to 8847
PORT=${MCP_SERVER_PORT:-8847}

echo "=================================================="
echo "📦 Adding LLM Context Prep to Claude Code"
echo "=================================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:$PORT/sse > /dev/null 2>&1; then
    echo "⚠️  Server is not running on port $PORT!"
    echo ""
    echo "Please start the server first:"
    echo "  ./run_sse_server.sh"
    echo ""
    echo "Then run this script again in a new terminal."
    exit 1
fi

echo "✅ Server is running on port $PORT"
echo ""
echo "Adding to Claude Code..."

claude mcp add --transport sse llm-prep http://localhost:$PORT/sse

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully added to Claude Code!"
    echo ""
    echo "Test it by typing /mcp in Claude Code"
else
    echo ""
    echo "❌ Failed to add to Claude Code"
    echo ""
    echo "Make sure you have Claude Code installed and configured"
fi
EOF

chmod +x add_to_claude.sh

print_success "Helper scripts created"

# Step 7: Test the installation
print_info "Testing installation..."

$PYTHON_VENV -c "import mcp; import fastapi; import uvicorn; print('✅ All modules imported successfully')"

if [ $? -ne 0 ]; then
    print_error "Some modules could not be imported"
    exit 1
fi

# Step 8: Final instructions
echo ""
echo "=================================================="
echo "🎉 Setup Complete!"
echo "=================================================="
echo ""
echo "📚 Next Steps:"
echo ""
echo "1. Start the MCP server:"
echo "   ${GREEN}./run_sse_server.sh${NC}"
echo ""
echo "2. In a new terminal, add to Claude Code:"
echo "   ${GREEN}./add_to_claude.sh${NC}"
echo ""
echo "3. Test in Claude Code by typing:"
echo "   ${GREEN}/mcp${NC}"
echo ""
echo "=================================================="
echo ""
echo "📖 Quick Command Reference:"
echo "  • Start server:    ./run_sse_server.sh"
echo "  • Add to Claude:   ./add_to_claude.sh"
echo "  • Run tests:       source venv/bin/activate && python scripts/test_server.py"
echo "  • View help:       make help"
echo ""
echo "📁 Your virtual environment is in: ${BLUE}venv/${NC}"
echo "   To activate manually: ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "=================================================="
echo ""

# Ask if user wants to start the server now
read -p "Would you like to start the server now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    print_info "Starting server..."
    echo ""
    ./run_sse_server.sh
fi