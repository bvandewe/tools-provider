# Agent Host Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy source code
COPY . .

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8050

# Default command (run from /app/src directory)
CMD ["sh", "-c", "cd /app/src && uvicorn main:create_app --factory --host 0.0.0.0 --port 8050"]
