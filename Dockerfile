FROM python:3.12-slim AS runtime

WORKDIR /app

# Install system deps then Python deps via uv
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml ./
RUN uv sync --frozen

COPY . .

# Run with uvicorn on port 8080 (matches docker-compose port mapping)
EXPOSE 8080

CMD ["uv", "run", "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
