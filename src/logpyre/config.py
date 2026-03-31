import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key")

    ELASTIC_HOST = os.environ.get("ELASTIC_HOST", "https://127.0.0.1:9200")
    ELASTIC_USER = os.environ.get("ELASTIC_USER", "elastic")
    ELASTIC_PASSWORD = os.environ.get("ELASTIC_PASSWORD", "")
    ELASTIC_CERT_FINGERPRINT = os.environ.get("ELASTIC_CERT_FINGERPRINT", "")
