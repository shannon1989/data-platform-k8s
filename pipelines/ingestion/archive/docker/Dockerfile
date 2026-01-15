FROM python:3.11-slim

# env
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# deps
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# code
COPY eth_realtime_watcher.py .
COPY eth_backfill_job.py .
COPY assets_backfill.py .
COPY definitions.py .

# Expose the port that your Dagster instance will run on
EXPOSE 3030

CMD ["dagster", "api", "grpc", \
     "-h", "0.0.0.0", \
     "-p", "3030", \
     "-f", "definitions.py"]