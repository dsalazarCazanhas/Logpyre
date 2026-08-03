# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
poetry install

# Run dev server
poetry run flask --app src/logpyre/app.py run --debug --reload

# Run all tests (no Elasticsearch required)
poetry run pytest -v

# Run a single test file
poetry run pytest tests/ingest/parsers/nginx_combined/test_parser.py -v

# Lint
poetry run ruff check src/
```

## Architecture

**Logpyre** is a Flask + Elasticsearch log ingestion and search tool. Users upload log files, choose a format, and the app parses and indexes them. Search results are displayed via AG Grid on the frontend.

### Application factory (`src/logpyre/app.py`)

`create_app()` is the entry point. It reads settings from `config.py` (pydantic-settings), registers extensions (CORS, Moment, Bootstrap), calls `init_elastic()` to create the shared ES connection pool, and registers the `web` Blueprint.

### Configuration (`src/logpyre/config.py`)

All environment variables are declared as a single `Settings` class (pydantic-settings). A module-level `settings` singleton is imported across the codebase. Production mode (`APP_ENV=production`) enforces stricter validation: non-default secret key, non-default ES password, a TLS fingerprint, and restricted CORS origins.

### Elasticsearch layer (`src/logpyre/elastic/`)

- `client.py` — `init_elastic()` stores the client in `app.extensions["logpyre_elastic"]`; `get_client()` retrieves it within a request context. TLS: fingerprint-based in production, verification disabled in dev.
- `index.py` — `index_document()` writes one parsed doc to ES. Index name is derived from the document's `log_format` field.
- `search.py` — `search_logs()` runs paginated full-text search.
- `formats.py` — persists `column_defs` and `format_label` into a `logpyre-formats` ES index so the search endpoint doesn't depend on the in-process parser registry for rendering metadata.
- `projects.py` — tracks which project slugs exist by querying indexed documents.

### Ingest pipeline (`src/logpyre/ingest/`)

1. `pipeline.py` — `ingest_file(stream, format_name, project)` reads line-by-line, calls `parse_line_with_format()`, stamps the doc with the project slug, and calls `index_document()`. A per-line failure never aborts the pipeline.
2. `parser.py` — maintains `_PARSERS`, an ordered list of parser instances. `parse_line()` tries each in order via `can_parse()`. Auto-detection is bypassed at upload time — the user picks the format explicitly, so `parse_line_with_format()` is used instead.
3. `parsers/base.py` — `BaseParser` is a `Protocol` (structural subtyping). Parsers do **not** inherit from it; they just implement the interface.
4. `models.py` — `BaseLogDocument` (Pydantic) is the base for all document types. Format-specific models subclass it.

### Web layer (`src/logpyre/web/`)

A single Blueprint (`web`) in `routes.py`. Key routes:
- `GET /` — renders the main page with the upload form and the AG Grid viewer
- `GET /upload`, `POST /upload` — handles file upload; validates project slug uniqueness before ingesting
- `GET /api/search` — paginated search; returns `hits`, pagination metadata, `column_defs`, and `format_label`
- `GET /api/projects` — list project slugs
- `GET /api/formats` — list registered parser formats
- `GET /health` — ES connectivity check

### Adding a new parser

1. Create `src/logpyre/ingest/parsers/<format_name>.py` satisfying `BaseParser` (duck typing — no inheritance).
2. Register an instance in `_PARSERS` in `parser.py`. Order matters: `can_parse()` is tried top-to-bottom.
3. If the format has new fields, add a Pydantic model in `models.py` subclassing `BaseLogDocument`.
4. Add a `column_defs` list on the parser class — this drives the AG Grid columns in the frontend.
5. Add tests at `tests/ingest/parsers/<format_name>/test_parser.py` covering metadata, happy path, and error cases.
6. Optionally add a `README.md` inside `src/logpyre/ingest/parsers/<format_name>/`.

### Tests

Tests do **not** need a running Elasticsearch. `tests/conftest.py` injects stub env vars so `Settings` loads without errors and no real ES connection is attempted.

## Key conventions

- `format_name` slugs must match `^[a-z][a-z0-9_]*$` — used directly in ES index names.
- Parsers raise `ValueError` on bad input; they never silently return partial data.
- Branch naming: `<type>/[<scope>-]<short-description>` — e.g. `feat/parser-apache_combined-add-parser`.
- All project-facing text (code, comments, commits, docs) in **English**.
- Every non-trivial change goes through: Proposal → Analysis → Execution. Never implement without user approval of the proposal.
- Never delete files, branches, or ES indices without explicit confirmation.
