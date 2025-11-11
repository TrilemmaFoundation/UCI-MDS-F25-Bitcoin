import streamlit as st

# from dashboard.backend.gsheet_utils import update_user_preferences
from dashboard.backend.supabase_utils import (
    update_user_preferences,
    get_user_info_by_email,
)

import time
import pandas as pd
from dashboard.config import get_today


def modal(email: str):
    if email:
        with st.popover(
            "Update info",
        ):
            st.markdown("Save your investment info")
            user_info = get_user_info_by_email(email)
            budget = st.number_input(
                "What's your budget?", value=int(float(user_info["budget"])), step=100
            )
            start_date = st.date_input(
                "Start date",
                value=get_today(),
            )
            investment_period = st.number_input(
                "Investment window (months)", value=int(user_info["investment_period"])
            )
            # boost_factor = st.slider(
            #     "Update Boost Factor (α)",
            #     0.5,
            #     5.0,
            #     1.25,
            #     0.05,
            #     help="Controls how aggressively to buy during dips.",
            # )

            save_button = st.button("Save your preferences")

            if save_button:
                date_formatted = start_date.strftime("%Y-%m-%d")
                saved_preferences = {
                    "user_email": st.user.get("email"),
                    "budget": budget,
                    "start_date": date_formatted,
                    "investment_period": investment_period,
                    "boost_factor": 1.25,
                }
                update_user_preferences(saved_preferences)
                st.toast("Your investment preferences have been saved!")
                time.sleep(1)
                st.rerun()
