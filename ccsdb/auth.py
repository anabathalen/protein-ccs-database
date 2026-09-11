"""Authentication and application-level email authorization."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from .config import (
    app_environment,
    approved_emails,
    auth_configured,
    auth_provider,
    local_user_email,
)


@dataclass(frozen=True)
class Identity:
    email: str
    suggested_name: str


def require_identity() -> Identity:
    """Require an authenticated identity whose email is on the allowlist."""

    if auth_configured():
        if not st.user.is_logged_in:
            st.title("Crowdsourced Protein CCS Database")
            st.write("Sign in with an approved email address to continue.")
            st.button("Sign in", on_click=st.login, args=(auth_provider(),), type="primary")
            st.stop()
        email = str(st.user.get("email", "")).strip().lower()
        suggested_name = str(st.user.get("name", "") or email.split("@", 1)[0]).strip()
        identity = Identity(email=email, suggested_name=suggested_name)
    elif app_environment() == "development":
        email = local_user_email()
        identity = Identity(email=email, suggested_name=email.split("@", 1)[0].title())
    else:
        st.error("Authentication has not been configured for this production app.")
        st.stop()

    allowlist = approved_emails()
    if not identity.email or identity.email not in allowlist:
        st.error("This email address is not approved to use the database.")
        if auth_configured() and st.user.is_logged_in:
            st.button("Sign out", on_click=st.logout)
        st.stop()
    return identity
