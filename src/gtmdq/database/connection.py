"""Credentials are read from environment; connection strings are never logged."""

import os

import psycopg
from dotenv import load_dotenv

from gtmdq.config import PROJECT_ROOT


def connect() -> psycopg.Connection:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    password = os.environ.get("POSTGRES_PASSWORD", "")
    if not password or password == "replace-with-a-local-password":
        raise ValueError("Configure POSTGRES_PASSWORD in .env (run scripts/init_env.py)")
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "gtmdq"),
        user=os.environ.get("POSTGRES_USER", "gtmdq"),
        password=password,
        connect_timeout=10,
    )
