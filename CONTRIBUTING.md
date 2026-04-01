# Contributing to Logpyre

Thank you for your interest in contributing. This document explains how to get
a local environment running, how the project is structured, and the conventions
you need to follow before opening a pull request.

---

## Prerequisites

| Tool | Minimum version | Notes |
| --- | --- | --- |
| Python | 3.10 | 3.14 used in CI |
| Poetry | 1.8 | dependency management and virtual env |
| Docker | any recent | used to run Elasticsearch locally |
| Git | any recent | |

---

## Local environment setup

## 1. Clone and install

```bash
git clone https://github.com/dsalazarCazanhas/Logpyre.git
cd indexPy
poetry install
```

## 2. Configure

`cp .env.example .env`

### Open .env and fill in at minimum

### FLASK_SECRET_KEY=`<any random string>`

### ELASTIC_PASSWORD=`<password you set when starting ES>`

## 3. Start Elasticsearch in Docker (development mode — single node, no heap limit)

```bash
docker network create elastic
docker run -d --rm --name elasticsearch -p 9200:9200 --net elastic -m 1GB -e "discovery.type=single-node" -e "ELASTIC_PASSWORD=changeme" elasticsearch:9.3.2
```

## 4. Run the app

`poetry run flask --app src/logpyre/app.py run --debug --reload`

## 5. Verify connectivity

`curl -k https://localhost:5000/health`

> **TLS note** — Elasticsearch 8 uses self-signed TLS by default. Leave
> `ELASTIC_CERT_FINGERPRINT` unset in development; the client will skip
> certificate verification and log a warning. Never do this in production.

---

## Running the tests

Tests do **not** require a real Elasticsearch instance. `conftest.py` stubs
the required environment variables so all parser and dispatcher tests run
fully in-process.

```bash
poetry run pytest -v
# Expected: 87 passed
```

All tests must pass before opening a pull request. Do not bypass hooks with
`--no-verify`.

---

## Project layout

```bash
src/logpyre/
├── app.py                  # Application factory (create_app)
├── config.py               # pydantic-settings — all env vars live here
├── elastic/
│   ├── client.py           # ES connection pool, init_elastic()
│   ├── formats.py          # upsert/get format metadata in logpyre-formats index
│   ├── index.py            # index_document() — writes one doc to ES
│   └── search.py           # search_logs() — paginated full-text search
├── ingest/
│   ├── models.py           # Pydantic models: BaseLogDocument, NginxLogDocument
│   ├── parser.py           # Parser registry and dispatch functions
│   ├── pipeline.py         # ingest_file() — reads a stream, parses, indexes
│   ├── request_classifier.py
│   └── parsers/
│       ├── base.py         # BaseParser Protocol (structural typing — no ABC)
│       ├── combined.py     # Nginx combined log parser
│       └── json_log.py     # Nginx JSON structured log parser
└── web/
    ├── forms.py            # Flask-WTF forms
    └── routes.py           # All HTTP routes (Blueprint "web")

tests/
└── ingest/
    ├── parsers/
    │   ├── nginx_combined/ # Per-format test suite
    │   └── nginx_json/
    └── test_parser_dispatcher.py
```

---

## How to add a new parser

### 1. Create the parser module

```bash
src/logpyre/ingest/parsers/<format_name>.py
```

The file must define a class that satisfies the `BaseParser` Protocol
(structural subtyping — no inheritance required):

```python
from logpyre.ingest.models import BaseLogDocument   # or a subclass

class MyFormatParser:
    format_name:  str       = "my_format"           # ^[a-z][a-z0-9_]*$
    format_label: str       = "My Format"           # shown in the UI
    column_defs:  list[dict] = [                    # drives the AG Grid columns
        {"field": "timestamp",  "headerName": "Timestamp", "width": 158,
         "sortable": True, "sort": "desc", "renderer": "timestamp"},
        # … one entry per field you want displayed
    ]

    def can_parse(self, line: str) -> bool:
        """Return True if this parser recognises the line format."""
        ...

    def parse(self, line: str) -> BaseLogDocument:
        """Parse the line and return a fully populated document.
        Raises ValueError on invalid input.
        """
        ...
```

`column_defs` key reference:

| Key | Type | Description |
| --- | --- | --- |
| `field` | str | Document field name — **required** |
| `headerName` | str | Column header label — **required** |
| `width` | int | Fixed pixel width |
| `flex` | int | Flex ratio (mutually exclusive with `width`) |
| `minWidth` | int | Minimum width when using `flex` |
| `sortable` | bool | Enable sort on this column |
| `sort` | `"asc"` \| `"desc"` | Default sort direction |
| `filter` | str | AG Grid filter type (e.g. `"agTextColumnFilter"`) |
| `wrapText` | bool | Enable word-wrap and auto row height |
| `renderer` | str | Key in the frontend `RENDERERS` map (see below) |
| `type` | str | AG Grid column type (e.g. `"numericColumn"`) |

### 2. Add a parser README

Create `src/logpyre/ingest/parsers/<format_name>/README.md` with a brief
description of the format (see the existing parsers for the template).

### 3. Register the parser

Open `src/logpyre/ingest/parser.py` and add an instance to `_PARSERS`:

```python
from .parsers.my_format import MyFormatParser

_PARSERS: list[BaseParser] = [
    JsonLogParser(),
    MyFormatParser(),   # ← add here
    CombinedParser(),
]
```

> **Order matters.** Parsers are tried top-to-bottom in `parse_line()`.
> Put cheaper or more specific detectors first.

### 4. Add a Pydantic model (if needed)

If the new format has fields not covered by `NginxLogDocument`, define a new
model subclassing `BaseLogDocument` in `src/logpyre/ingest/models.py`:

```python
class MyFormatDocument(BaseLogDocument):
    my_field: str
    another_field: int | None = None
```

### 5. Add frontend renderers (if needed)

If `column_defs` references a `renderer` key that does not exist in
`RENDERERS` inside `src/logpyre/templates/index.html`, add it:

```js
const RENDERERS = {
    // … existing renderers …
    my_renderer: p => p.value ? escapeHtml(String(p.value)) : "",
};
```

### 6. Write tests

Create the test suite at:

```bash
tests/ingest/parsers/<format_name>/
├── __init__.py
└── test_parser.py
```

Minimum test classes to include (follow the existing suites as templates):

| Class | Tests |
| --- | --- |
| `TestMyFormatParserFormatMetadata` | `format_name`, `format_label`, `column_defs` structure, `doc.log_format` matches parser |
| `TestMyFormatParserHappyPath` | Every field extracted correctly, types validated |
| `TestMyFormatParserErrors` | `can_parse` returns False for unrelated lines, `parse` raises `ValueError` on bad input |

---

## Git workflow

### Branch naming

Branches must follow this pattern:

```git
<type>/[<scope>-]<short-description>
```

| Segment | Values | Example |
| --- | --- | --- |
| `type` | `feat`, `fix`, `chore`, `docs`, `refactor`, `test` | `feat` |
| `scope` | optional — use the **parser format_name** when the work is parser-specific | `parser-apache_combined` |
| `short-description` | lowercase, hyphen-separated, imperative | `add-method-renderer` |

**Examples:**

```git
feat/parser-apache_combined-add-parser
fix/parser-nginx_json-handle-missing-referer
chore/update-elasticsearch-client
docs/contributing-setup-instructions
refactor/parser-nginx_combined-simplify-regex
test/parser-apache_combined-add-edge-cases
```

The parser `format_name` (e.g. `nginx_combined`, `apache_combined`) goes in
the scope segment so pull requests are immediately identifiable by format.

### Commits

- Imperative mood, English: `Add X`, `Fix Y`, `Remove Z`
- Keep commits atomic — one logical change per commit
- Reference issues when applicable: `Fix status parsing for 3xx responses (#42)`

### Before opening a PR

```bash
poetry run pytest -v          # all tests must pass
poetry run ruff check src/    # no linting errors
```

---

## Code conventions

- **Language:** All code, comments, docstrings, commit messages, branch names,
  PR titles, and documentation must be written in **English**.
- **Parsers:** implement the `BaseParser` Protocol via duck typing — do not
  inherit from any base class.
- **`format_name`:** must match `^[a-z][a-z0-9_]*$` — it is used directly in
  Elasticsearch index names.
- **Error handling:** parsers raise `ValueError` on bad input; they never
  silently return partial data.
- **No over-engineering:** only add what was explicitly requested. Helpers and
  abstractions for one-time operations are discouraged.
