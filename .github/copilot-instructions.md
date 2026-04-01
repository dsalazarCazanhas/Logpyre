# Copilot Instructions — Logpyre

## Language

- **Chat and conversations:** always respond in Spanish (es).
- **Everything project-facing** (code comments, docstrings, commit messages, branch names, PR titles and descriptions, issue text, documentation, README): always write in English (en).

## Change workflow

Every non-trivial change must follow three phases in order.
Never move to the next phase without explicit user approval.

### 1. Propuesta
Describe *what* will change and *why*.
List the affected files and the expected outcome.
Do not write any code yet.

### 2. Análisis
Review the relevant existing code in detail.
Identify risks, edge cases, and dependencies.
Confirm the approach is sound before touching anything.

### 3. Ejecución
Implement the agreed-upon change.
Keep the scope strictly limited to what was approved in the propuesta.
Run tests if applicable and report the result.

## Additional rules

- Never delete files, branches, or Elasticsearch indices without explicit confirmation.
- Never skip `--no-verify` or bypass git hooks.
- Avoid over-engineering: only add what was explicitly requested.
- Keep commits atomic and descriptive in imperative form ("Add X", "Fix Y", "Remove Z").
