FROM python:3.11-slim as builder

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY code_review_assistant/ ./code_review_assistant/
COPY .env.example .env

FROM python:3.11-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "adk api_server code_review_assistant --port ${PORT:-8080} --host 0.0.0.0"]