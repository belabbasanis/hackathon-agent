FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files first for layer caching (poetry.lock is gitignored, so not in repo)
COPY pyproject.toml ./

# Install dependencies (no dev deps, no virtualenv inside container)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code (env vars come from AgentCore runtime config)
COPY src/ src/

# Listen on 8080 (Railway / AgentCore). In Railway "Generate Domain" use port 8080.
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request, os; p=os.getenv('PORT','8080'); u='http://127.0.0.1:'+p+'/.well-known/agent.json'; urllib.request.urlopen(u)" || exit 1

# Run the AgentCore-aware A2A server
CMD ["python", "-m", "src.agent_a2a_agentcore"]
