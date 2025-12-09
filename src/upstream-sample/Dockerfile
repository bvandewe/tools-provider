# Pizzeria Backend - Sample Upstream Service
# Demonstrates RBAC integration with Keycloak

FROM python:3.11-slim

WORKDIR /app

# Copy project files needed for installation
COPY pyproject.toml README.md ./

# Install dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
