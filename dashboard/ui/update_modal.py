import streamlit as st
from backend.gsheet_utils import update_user_preferences
import time


def modal():
    if st.user.get("email"):
        with st.popover(
            "Update your saved investment parameters",
        ):
            st.markdown("Save your investment info")
            budget = st.number_input("What's your budget?", value=1000, step=100)
            start_date = st.date_input(
                "Start date",
                value="today",
            )
            investment_period = st.number_input("Investment window (months)", value=12)
            boost_factor = st.slider(
                "Update Boost Factor (α)",
                0.5,
                5.0,
                1.25,
                0.05,
                help="Controls how aggressively to buy during dips.",
            )

            save_button = st.button("Save your preferences")

            if save_button:
                date_formatted = start_date.strftime("%Y-%m-%d")
                saved_preferences = {
                    "user_email": st.user.get("email"),
                    "budget": budget,
                    "start_date": date_formatted,
                    "investment_period": investment_period,
                    "boost_factor": boost_factor,
                }
                update_user_preferences(saved_preferences)
                st.toast("Your investment preferences have been saved!")
                time.sleep(1)
                st.rerun()
