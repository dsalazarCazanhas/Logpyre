import re

# Matches logpyre-{project}-{format}-YYYY.MM.DD
# Format names use only [a-z0-9_] so the last two segments are unambiguous.
_DATA_INDEX_RE = re.compile(
    r"^logpyre-(?P<project>.+)-[a-z][a-z0-9_]*-\d{4}\.\d{2}\.\d{2}$"
)


def project_exists(slug: str) -> bool:
    """Return True if *slug* already has at least one data index.

    Checks ``logpyre-{slug}-*`` directly against Elasticsearch — the same
    source of truth used by :func:`list_projects`.  Does NOT rely on the
    ``logpyre-projects`` registry, so it correctly detects legacy projects that
    were indexed before the registry existed.

    Does NOT swallow exceptions — callers must handle connection errors.
    Returns ``False`` only when no matching data index is found.

    Args:
        slug: Project slug to check (e.g. ``"frontend"``).
    """
    from .client import get_client
    from elasticsearch import NotFoundError

    try:
        entries: list[dict[str, str]] = get_client().cat.indices(  # type: ignore[assignment]
            index=f"logpyre-{slug}-*",
            h="index",
            format="json",
        )
        return any(_DATA_INDEX_RE.match(e["index"]) for e in entries)
    except NotFoundError:
        return False


def list_projects() -> list[str]:
    """Return a sorted list of project slugs inferred from data indices.

    Reads ``logpyre-*`` index names directly — always reflects the real state
    of the data regardless of whether ``logpyre-projects`` is up to date.
    Returns an empty list when ES is unavailable or no data indices exist.
    """
    from .client import get_client

    try:
        entries: list[dict[str, str]] = get_client().cat.indices(  # type: ignore[assignment]
            index="logpyre-*,-logpyre-formats,-logpyre-projects",
            h="index",
            format="json",
        )
        slugs: set[str] = set()
        for entry in entries:
            m = _DATA_INDEX_RE.match(entry["index"])
            if m:
                slugs.add(m.group("project"))
        return sorted(slugs)
    except Exception:
        return []
