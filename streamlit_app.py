"""Crowdsourced Protein CCS Database Streamlit entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ccsdb.auth import require_identity
from ccsdb.config import auth_configured, database_url
from ccsdb.database import Database
from ccsdb.pages import (
    render_add_entry,
    render_data,
    render_leaderboard,
    render_papers,
    render_visualize,
)

st.set_page_config(
    page_title="Crowdsourced Protein CCS Database",
    layout="wide",
    initial_sidebar_state="expanded",
)

STYLE_PATH = Path(__file__).with_name("static") / "styles.css"
st.markdown(f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


@st.cache_resource
def get_database(url: str) -> Database:
    database = Database(url)
    database.initialize()
    return database


def complete_profile(database: Database, user: dict[str, Any]) -> dict[str, Any]:
    if user.get("profile_complete") or st.session_state.get("profile_complete"):
        return user
    st.title("Choose your nickname")
    st.write("This is the name that will appear beside your contributions and on the leaderboard.")
    with st.form("first_profile"):
        nickname = st.text_input("Nickname", value=user["nickname"], max_chars=40)
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        try:
            user["nickname"] = database.update_nickname(user["id"], nickname)
            user["profile_complete"] = True
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["profile_complete"] = True
            st.rerun()
    st.stop()


def sidebar_profile(database: Database, user: dict[str, Any]) -> None:
    st.sidebar.markdown("### Crowdsourced Protein CCS Database")
    st.sidebar.caption(user["email"])
    with st.sidebar.expander(f"Signed in as {user['nickname']}"):
        with st.form("nickname_form"):
            nickname = st.text_input("Nickname", value=user["nickname"], max_chars=40)
            save = st.form_submit_button("Save nickname")
        if save:
            try:
                user["nickname"] = database.update_nickname(user["id"], nickname)
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("Nickname saved")
        if auth_configured():
            st.button("Sign out", on_click=st.logout)


def main() -> None:
    database = get_database(database_url())
    identity = require_identity()
    try:
        user = database.ensure_user(identity.email, identity.suggested_name)
    except PermissionError as error:
        st.error(str(error))
        st.stop()
    user = complete_profile(database, user)
    sidebar_profile(database, user)

    if pending_page := st.session_state.pop("navigation_pending", None):
        st.session_state["navigation"] = pending_page

    page = st.sidebar.radio(
        "Navigation",
        ["Data", "Papers", "Add entry", "Visualize", "Leaderboard"],
        key="navigation",
    )
    if page == "Data":
        render_data(database, user)
    elif page == "Papers":
        render_papers(database, user)
    elif page == "Add entry":
        render_add_entry(database, user)
    elif page == "Visualize":
        render_visualize(database)
    else:
        render_leaderboard(database)


if __name__ == "__main__":
    main()
