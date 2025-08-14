# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies (tree command for better project visualization)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tree \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash mcp && \
    mkdir -p /workspace /app && \
    chown -R mcp:mcp /workspace /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/mcp/.local

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=mcp:mcp src/ ./src/
COPY --chown=mcp:mcp prompts/ ./prompts/
COPY --chown=mcp:mcp scripts/ ./scripts/

# Switch to non-root user
USER mcp

# Add local bin to PATH
ENV PATH=/home/mcp/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# MCP server configuration
ENV MCP_DOCKER_MODE=true
ENV MCP_WORKSPACE_DIR=/workspace

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Volume for workspace
VOLUME ["/workspace"]

# Default command - run as stdio MCP server (best for Claude Code)
CMD ["python", "src/mcp_server_fastmcp.py", "--transport", "stdio"]

