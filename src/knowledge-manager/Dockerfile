# Knowledge Manager Dockerfile
# Multi-stage build for production deployment

FROM python:3.12-slim as builder

WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.2

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Export requirements (without dev dependencies)
RUN poetry export -f requirements.txt --without-hashes --without dev > requirements.txt

# Production stage
FROM python:3.12-slim as production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from builder
COPY --from=builder /app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
