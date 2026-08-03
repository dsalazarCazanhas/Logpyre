import re

# Matches logpyre-{project}-{format}-YYYY.MM.DD
# Format names use only [a-z0-9_] so the last two segments are unambiguous.
_DATA_INDEX_RE = re.compile(
    r"^logpyre-(?P<project>.+)-[a-z][a-z0-9_]*-\d{4}\.\d{2}\.\d{2}$"
)

# Metadata index names — never valid project slugs. "logpyre-{slug}-*" would
# otherwise also match "logpyre-formats"/"logpyre-projects" if a project were
# ever named this way, wiping shared metadata instead of one project's data.
_RESERVED_SLUGS = {"formats", "projects"}


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
    from elasticsearch import NotFoundError

    from .client import get_client

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


def delete_project(slug: str) -> int:
    """Delete every data index belonging to *slug* from Elasticsearch.

    Uses the same ``logpyre-{slug}-*`` pattern as :func:`project_exists`, so a
    project with no matching indices deletes nothing and returns 0 — this is
    idempotent, not an error.

    Does NOT swallow ES connectivity errors — callers must handle those.

    Args:
        slug: Project slug to delete.

    Returns:
        The number of indices deleted.

    Raises:
        ValueError: If slug is a reserved metadata index name.
    """
    if slug in _RESERVED_SLUGS:
        raise ValueError(f"{slug!r} is a reserved name and cannot be deleted as a project.")

    from elasticsearch import NotFoundError

    from .client import get_client

    client = get_client()
    index_pattern = f"logpyre-{slug}-*"
    try:
        entries: list[dict[str, str]] = client.cat.indices(  # type: ignore[assignment]
            index=index_pattern,
            h="index",
            format="json",
        )
    except NotFoundError:
        return 0

    count = len(entries)
    if count:
        # Elasticsearch's destructive_requires_name safety setting rejects
        # wildcard deletes (400 "Wildcard expressions ... are not allowed"),
        # so delete the exact index names resolved above instead of the
        # pattern itself.
        index_names = ",".join(e["index"] for e in entries)
        client.indices.delete(index=index_names, ignore_unavailable=True)
    return count
