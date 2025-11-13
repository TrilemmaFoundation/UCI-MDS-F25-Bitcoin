import streamlit as st

# from dashboard.backend.gsheet_utils import add_user_info_to_sheet, does_user_exist
from dashboard.backend.supabase_utils import add_user_info_to_sheet, does_user_exist

from dashboard.config import get_today  # Use the centralized get_today() constant


def authenticate():
    """
    Handle authentication and display appropriate UI.
    Returns True if user is authenticated, False otherwise.
    """
    # Handle logout via query params first
    query_params = st.query_params
    if query_params.get("logout") == "true":
        st.logout()
        st.query_params.clear()  # Clear query params after logout
        st.rerun()

    # Check if user is authenticated with valid data
    if st.user and st.user.get("email"):
        # User is logged in with valid data

        # Add user to database if they don't exist
        if not does_user_exist(st.user.get("email")):
            to_add = {
                "user_email": st.user.get("email"),
                "budget": 1000,
                # Use the consistent get_today() from config
                "start_date": get_today().strftime("%Y-%m-%d"),
                "investment_period": 12,
                "boost_factor": 1.25,
                "email_opted_in": 0,
            }
            add_user_info_to_sheet(to_add)

        # Show welcome message in sidebar
        with st.sidebar:
            if st.user.get("name"):
                with st.expander(f"Welcome, {st.user.get('name').split(' ')[0]}!"):
                    st.write(
                        f"You're logged in, so we've saved your investment details."
                    )
        # Get provider for display
        provider = st.user.get("sub", "unknown|unknown").split("|")[0]

        # Inject CSS for profile dropdown
        st.markdown(
            """
        <style>
            .profile-dropdown {
                position: fixed;
                top: 4rem;
                right: 1rem;
                z-index: 2000;
            }
            .profile-img {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                cursor: pointer;
                display: block;
            }
            
            .dropdown-content {
                display: none;
                position: absolute;
                right: 0;
                top: 45px;
                background-color: #1F2324;
                min-width: 200px;
                box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
                padding: 16px;
                border-radius: 8px;
                font-size: 14px;
                border: 1px solid #e0e0e0;
            }
            .profile-dropdown:hover .dropdown-content {
                display: block;
            }
            .dropdown-content::before {
                content: '';
                position: absolute;
                top: -1rem;
                left: 0;
                right: 0;
                height: 1rem;
                background: transparent;
                pointer-events: auto;
            }
            .logout-button {
                margin-top: 12px;
                width: 100%;
                background: #1a080e;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 13px;
                font-family: inherit;
            }
            .logout-button:hover {
                background: #153d4d;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )

        # Render profile dropdown
        # print(st.user.to_dict())
        # st.image(st.user.get("picture"))
        st.markdown(
            f"""
        <div class="profile-dropdown">
            <img src="{st.user.get("picture", "")}" alt="Profile Picture" class="profile-img">
            <div class="dropdown-content">
                <div>Howdy, <strong>{st.user.get("name", "User").split(' ')[0]}</strong></div>
                <div style="margin-top:6px; font-size:13px;">
                    Logged in via {provider}
                </div>
                <a href="?logout=true" class="logout-button" style="text-decoration: none; display: block; text-align: center;">Log out</a>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return True
    else:
        # User not logged in or invalid session, show login in sidebar
        with st.sidebar:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Log in", type="secondary"):
                    st.login()
            with col2:
                st.image("dashboard/images/bitcoin_logo.svg")
        return False
