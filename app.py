import streamlit as st
from dashboard.ui.authentication import authenticate


def initialize_user_session():
    """Initialize user session and tracking."""
    # Authenticate user first
    authenticate()

    # Get user email and create/update user record
    user_email = st.user.get("email")
    user_name = st.user.get("name", "")

    return user_email, user_name


initialize_user_session()


pg = st.navigation(
    [
        "dashboard/Daily_Schedule.py",
        "dashboard/Advanced_Analytics.py",
        "dashboard/News_Social.py",
        "dashboard/About.py",
    ]
)
pg.run()
