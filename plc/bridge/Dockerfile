FROM python:3.12-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 plcbridge && \
    chown -R plcbridge:plcbridge /app
USER plcbridge

# Expose the SSE server port
EXPOSE 7654

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7654/signals', timeout=5)" || exit 1

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Default command
CMD ["/app/entrypoint.sh"]