docker pull apache/airflow:3.0.2-python3.11

USER root

COPY . /opt/airflow/jobs/

# install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# deps
# COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# ENV PYTHONPATH=/opt/airflow

USER airflow