# Logpyre

Lightweight log ingestion and search tool built on Flask and Elasticsearch.

Upload log files, parse them into structured documents, and search across them
with the power of Elasticsearch's full-text indexing — without the complexity
of a full SIEM deployment.

## Stack

- **Python 3.10+**
- **Flask 3** — HTTP layer and server-side templates
- **Elasticsearch 9+** — indexing, storage, and search backend

## Getting started

```bash
# 1. Install dependencies
poetry install

# 2. Configure environment
cp env.example .env
# Edit .env with your Elasticsearch credentials

# 3. Run
flask --app .\src\logpyre\app.py run --debug --reload
```

## Docker

The repository ships a production-ready `Dockerfile` and a local development
stack in the `docker/` folder.

**`Dockerfile`** — multi-stage build that produces a minimal image:
- Stage `builder`: resolves dependencies from `poetry.lock` into an in-project
  virtualenv (no network access needed at runtime).
- Stage `runtime`: slim Python image, non-root user, Gunicorn as the WSGI
  server. Workers are configurable via `GUNICORN_WORKERS` (default: 2).

**`docker/compose.yml`** — brings up the full stack with a single command:
- `elasticsearch` — Elasticsearch 9 single-node, memory-capped at 1 GB, **not**
  exposed to the host (internal network only).
- `logpyre` — built from the `Dockerfile`, available at `http://localhost:5000`,
  waits for Elasticsearch to be healthy before starting.

```bash
# 1. Create your local env file (gitignored)
cp docker/env.docker docker/.env

# 2. Edit docker/.env — at minimum change ELASTIC_PASSWORD and FLASK_SECRET_KEY

# 3. Start the stack
docker compose -f docker/compose.yml up --build
```

To enable TLS verification (recommended for production), extract the
Elasticsearch CA fingerprint after the first start:

```bash
docker cp elasticsearch:/usr/share/elasticsearch/config/certs/http_ca.crt .
openssl x509 -fingerprint -sha256 -noout -in http_ca.crt
# → SHA256 Fingerprint=AA:BB:CC:...
```

Paste the value into `docker/.env` as `ELASTIC_CERT_FINGERPRINT` and set
`APP_ENV=production`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, how to add a new
parser, branch naming conventions, and the pre-PR checklist.

## License

Apache 2.0 — see [LICENSE](LICENSE).
