"""Runtime configuration with secrets kept outside source control."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{ROOT / 'data' / 'protein_ccs.db'}"


def _secret(path: tuple[str, ...], default: Any = None) -> Any:
    value: Any = st.secrets
    try:
        for part in path:
            value = value[part]
    except (FileNotFoundError, KeyError, TypeError):
        return default
    return value


def database_url() -> str:
    """Read the database URL from the environment or Streamlit secrets."""

    url = str(os.getenv("DATABASE_URL") or _secret(("database", "url"), DEFAULT_DATABASE_URL))
    if app_environment() == "production" and url.startswith("sqlite"):
        raise RuntimeError("Production requires a persistent PostgreSQL database URL")
    return url


def app_environment() -> str:
    return str(os.getenv("APP_ENV") or _secret(("app", "environment"), "development")).lower()


def local_user_email() -> str:
    return str(os.getenv("LOCAL_USER_EMAIL") or _secret(("app", "local_user_email"), "ana@example.org")).lower()


def approved_emails() -> set[str]:
    """Return the application allowlist from secrets or an environment variable."""

    environment_value = os.getenv("APPROVED_EMAILS")
    if environment_value:
        values = environment_value.split(",")
    else:
        values = _secret(("access", "approved_emails"), [])
    return {str(value).strip().lower() for value in values if str(value).strip()}


def auth_configured() -> bool:
    try:
        return "auth" in st.secrets
    except FileNotFoundError:
        return False


def auth_provider() -> str:
    return str(_secret(("app", "auth_provider"), "auth0"))
