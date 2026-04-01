# ── Stage 1: dependency builder ────────────────────────────────────────────────
# Installs all production dependencies into an in-project virtualenv using Poetry.
# Only the resolved lockfile is used — no network access needed in the runtime stage.
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir "poetry==2.2.1" && \
    poetry config virtualenvs.in-project true

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction --no-ansi && \
    .venv/bin/pip install --no-cache-dir "gunicorn==25.3.0"


# ── Stage 2: runtime ────────────────────────────────────────────────────────────
# Minimal image: only the venv, the application source, and gunicorn.
# Runs as a non-root user for OWASP compliance.
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create a dedicated non-root user/group
RUN addgroup --system logpyre && \
    adduser  --system --ingroup logpyre --no-create-home logpyre

# Copy the virtualenv built in the previous stage (includes gunicorn)
COPY --from=builder /build/.venv /app/.venv

# Copy only the application source — no tests, no dev tooling
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER logpyre

EXPOSE 5000

# Health check: confirm the app is responding before marking the container healthy.
# start-period gives Elasticsearch time to be ready before the first check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')"

# 2 workers is a safe default for a single-node deployment.
# Override at runtime: docker run -e GUNICORN_WORKERS=4 ...
# Use `python -m gunicorn` with an absolute path to bypass the venv shebang
# (shebangs in copied venvs point to the builder stage path, which does not exist at runtime).
CMD ["sh", "-c", "/app/.venv/bin/python -m gunicorn --workers ${GUNICORN_WORKERS:-2} --bind 0.0.0.0:5000 'logpyre.app:create_app()'"]
