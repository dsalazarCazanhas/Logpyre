"""Root conftest.py — pytest fixtures and environment setup.

This file is loaded automatically by pytest before any test collection.
It sets the minimum environment variables required by pydantic-settings so
that importing logpyre modules never fails due to missing configuration,
regardless of whether a .env file is present.
"""
import os


# Set required env vars before any module is imported.
# These values are test-only and never used for real connections.
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ELASTIC_PASSWORD", "test-password")
os.environ.setdefault("APP_ENV", "development")
