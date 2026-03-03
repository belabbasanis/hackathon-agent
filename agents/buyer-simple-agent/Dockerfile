FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev deps, no virtualenv inside container)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code (env vars come from AgentCore runtime config)
COPY src/ src/

# To include the frontend, build it first (cd frontend && npm run build)
# then uncomment:
# COPY frontend/dist/ frontend/dist/

# AgentCore sets PORT; default to 8080
ENV PORT=8080

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + __import__('os').getenv('PORT', '8080') + '/ping')" || exit 1

# Run the AgentCore-aware web server
CMD ["python", "-m", "src.web_agentcore"]
