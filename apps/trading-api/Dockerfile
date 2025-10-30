# Multi-stage build for Python trading API
FROM python:3.11-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r trading && useradd -r -g trading trading

# Copy Python packages from builder
COPY --from=builder /root/.local /home/trading/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Copy shared libraries (adjust path as needed)
COPY ../../libs ./libs

# Set ownership and permissions
RUN chown -R trading:trading /app && \
    chmod +x /app/*.py

# Switch to non-root user
USER trading

# Add local Python packages to PATH
ENV PATH=/home/trading/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/libs:$PYTHONPATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]