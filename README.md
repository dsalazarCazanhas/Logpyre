# Logpyre

[![CI](https://github.com/dsalazarCazanhas/Logpyre/actions/workflows/ci.yml/badge.svg)](https://github.com/dsalazarCazanhas/Logpyre/actions/workflows/ci.yml)
[![Docker Hub](https://img.shields.io/docker/v/dsalazarcazanhas/logpyre?label=docker&sort=semver)](https://hub.docker.com/r/dsalazarcazanhas/logpyre)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Lightweight log ingestion and search tool built on Flask and Elasticsearch.

Some UI ideas are borrowed from tools like Splunk, but the goal here isn't to
match their scope. Logpyre is built for fast **trace analysis**, with
**portability and ease of use** as the actual priorities — every feature is
scoped and hardened deliberately, without piling on noise.

![Search view: daily volume chart, method/path facets, and the Timestamp + Event results grid](docs/images/search-view.png)

## Stack

- **Python 3.10+**
- **Flask 3** — HTTP layer and server-side templates
- **Elasticsearch 9.3.2 (wolfi)** — indexing, storage, and search backend

## Quickstart

```bash
poetry install
cp example.env .env            # fill in your Elasticsearch credentials
poetry run flask --app src/logpyre/app.py run --debug --reload
```

Open `http://127.0.0.1:5000`, upload a log file, pick its format, search.

## Docker

- **`Dockerfile`** — multi-stage production build: dependencies resolve in a
  builder stage, the runtime stage is a slim non-root image running Gunicorn
  (`GUNICORN_WORKERS`, default: 2).
- **`docker/compose.yml`** — local integration stack: builds that same
  Dockerfile alongside a single-node Elasticsearch.

```bash
cp docker/docker.env docker/.env   # edit if needed
docker compose -f docker/compose.yml up --build
```

For production, enable TLS verification: extract the Elasticsearch CA
fingerprint after the first start, then set `ELASTIC_CERT_FINGERPRINT` and
`APP_ENV=production` in `docker/.env`.

```bash
docker cp elasticsearch:/usr/share/elasticsearch/config/certs/http_ca.crt .
openssl x509 -fingerprint -sha256 -noout -in http_ca.crt
# → SHA256 Fingerprint=AA:BB:CC:...
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, how to add a new
parser, branch naming conventions, and the pre-PR checklist.

## License

Apache 2.0 — see [LICENSE](LICENSE).
