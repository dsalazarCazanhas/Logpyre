# Logpyre

Lightweight log ingestion and search tool built on Flask and Elasticsearch.

Upload log files, parse them into structured documents, and search across them
with the power of Elasticsearch's full-text indexing — without the complexity
of a full SIEM deployment.

## Stack

- **Python 3.10+**
- **Flask 3** — HTTP layer and server-side templates
- **Elasticsearch 8** — indexing, storage, and search backend

## Getting started

```bash
# 1. Install dependencies
poetry install

# 2. Configure environment
cp .env.example .env
# Edit .env with your Elasticsearch credentials

# 3. Run
poetry run flask --app src/logpyre/app:create_app run --debug
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
