#!/bin/bash

# LLM Context Prep MCP Server - Installation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/yourusername/llm-context-prep-mcp.git"
INSTALL_DIR="$HOME/.llm-context-prep-mcp"
IMAGE_NAME="llm-context-prep-mcp:latest"

echo -e "${GREEN}LLM Context Prep MCP Server - Installation${NC}"
echo "============================================"

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker found${NC}"
    
    # Check Claude Code (optional)
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}✓ Claude Code found${NC}"
        HAS_CLAUDE=true
    else
        echo -e "${YELLOW}⚠ Claude Code not found (optional)${NC}"
        HAS_CLAUDE=false
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        echo -e "${RED}Git is not installed. Please install Git first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Git found${NC}"
}

# Clone or update repository
install_repository() {
    echo -e "\n${YELLOW}Installing repository...${NC}"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "Repository already exists. Updating..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        echo "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    echo -e "${GREEN}✓ Repository installed at $INSTALL_DIR${NC}"
}

# Build Docker image
build_docker_image() {
    echo -e "\n${YELLOW}Building Docker image...${NC}"
    
    cd "$INSTALL_DIR"
    docker build -f docker/Dockerfile -t "$IMAGE_NAME" .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
    else
        echo -e "${RED}Failed to build Docker image${NC}"
        exit 1
    fi
}

# Create wrapper script
create_wrapper_script() {
    echo -e "\n${YELLOW}Creating wrapper script...${NC}"
    
    WRAPPER_SCRIPT="$HOME/.local/bin/llm-context-prep"
    mkdir -p "$HOME/.local/bin"
    
    cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
# LLM Context Prep MCP Server Wrapper

# Default to current directory as workspace
WORKSPACE="${WORKSPACE:-$(pwd)}"

# Run the Docker container
docker run -i --rm \
    -v "$WORKSPACE:/workspace" \
    -e MCP_DEBUG="${MCP_DEBUG:-false}" \
    llm-context-prep-mcp:latest "$@"
EOF
    
    chmod +x "$WRAPPER_SCRIPT"
    echo -e "${GREEN}✓ Wrapper script created at $WRAPPER_SCRIPT${NC}"
    
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo -e "${YELLOW}Note: Add ~/.local/bin to your PATH:${NC}"
        echo 'export PATH="$HOME/.local/bin:$PATH"'
    fi
}

# Configure Claude Code
configure_claude_code() {
    if [ "$HAS_CLAUDE" = true ]; then
        echo -e "\n${YELLOW}Configuring Claude Code...${NC}"
        
        echo "Would you like to add the MCP server to Claude Code? (y/n)"
        read -r response
        
        if [[ "$response" =~ ^[Yy]$ ]]; then
            # Add to Claude Code
            claude mcp add llm-prep \
                --env WORKSPACE_DIR='$(pwd)' \
                -- docker run -i --rm \
                -v '$(pwd):/workspace' \
                llm-context-prep-mcp:latest
            
            echo -e "${GREEN}✓ MCP server added to Claude Code${NC}"
            echo "Test with: /mcp in Claude Code"
        fi
    fi
}

# Test installation
test_installation() {
    echo -e "\n${YELLOW}Testing installation...${NC}"
    
    # Test Docker image
    echo "Testing Docker image..."
    if docker run --rm llm-context-prep-mcp:latest python -c "print('Docker test successful')"; then
        echo -e "${GREEN}✓ Docker image works${NC}"
    else
        echo -e "${RED}Docker image test failed${NC}"
        exit 1
    fi
    
    # Test wrapper script if it exists
    if [ -f "$HOME/.local/bin/llm-context-prep" ]; then
        echo "Testing wrapper script..."
        if "$HOME/.local/bin/llm-context-prep" python -c "print('Wrapper test successful')"; then
            echo -e "${GREEN}✓ Wrapper script works${NC}"
        else
            echo -e "${YELLOW}⚠ Wrapper script test failed (check PATH)${NC}"
        fi
    fi
}

# Print usage instructions
print_instructions() {
    echo -e "\n${GREEN}Installation Complete!${NC}"
    echo "===================="
    echo ""
    echo "Usage:"
    echo "------"
    
    if [ "$HAS_CLAUDE" = true ]; then
        echo "In Claude Code:"
        echo "  /mcp                    # Check MCP server status"
        echo "  /mcp__llm_prep__debug_workflow  # Start debug workflow"
        echo ""
    fi
    
    echo "Docker command:"
    echo "  docker run -it --rm -v \$(pwd):/workspace llm-context-prep-mcp:latest"
    echo ""
    
    if [ -f "$HOME/.local/bin/llm-context-prep" ]; then
        echo "Wrapper script:"
        echo "  llm-context-prep"
        echo ""
    fi
    
    echo "Documentation:"
    echo "  $INSTALL_DIR/README.md"
    echo ""
    echo -e "${GREEN}Happy debugging!${NC}"
}

# Main installation flow
main() {
    check_prerequisites
    install_repository
    build_docker_image
    create_wrapper_script
    configure_claude_code
    test_installation
    print_instructions
}

# Run main function
main "$@"
