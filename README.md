# Logpyre

Lightweight log ingestion and search tool built on Flask and Elasticsearch.

Upload log files, parse them into structured documents, and search across them
with the power of Elasticsearch's full-text indexing — without the complexity
of a full SIEM deployment.

## Stack

- **Python 3.10+**
- **Flask 3** — HTTP layer and server-side templates
- **Elasticsearch 9.3.2 (wolfi)** — indexing, storage, and search backend

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

The repository ships a production-ready `Dockerfile` and a `docker/compose.yml`
file for local integration testing.

**Local development** should be done with Flask directly on your PC:

```bash
poetry install
cp env.example .env
# edit .env with your Elasticsearch credentials
flask --app src/logpyre.app run --debug --reload
```

**Production image** is built from the root `Dockerfile`.

**`Dockerfile`** — multi-stage build that produces a minimal image:
- Stage `builder`: resolves dependencies from `poetry.lock` into an in-project
  virtualenv (no network access needed at runtime).
- Stage `runtime`: slim Python image, non-root user, Gunicorn as the WSGI
  server. Workers are configurable via `GUNICORN_WORKERS` (default: 2).

**`docker/compose.yml`** — integration test stack that builds the same
`Dockerfile` used for production and verifies the full app + Elasticsearch
locally.

```bash
cp docker/env.docker docker/.env
# edit docker/.env if needed
docker compose -f docker/compose.yml up --build
```

To build the production image for CI or publishing:

```bash
docker build -t dsalazarcazanhas/logpyre:latest .
docker push dsalazarcazanhas/logpyre:latest
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
