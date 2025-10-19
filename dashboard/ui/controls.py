# ui/controls.py
import streamlit as st
import pandas as pd
import dashboard.config as config
from datetime import datetime


def render_controls(df_btc, investment_window):
    """
    Renders date selection and time control panel.
    Returns start_date (Timestamp), current_day (0-based int), and df_window.
    """
    st.markdown("### 📅 Select Accumulation Period")
    col1, col2 = st.columns(2)

    # --- Date Selection ---
    min_start_date = df_btc.index.min().date()
    max_start_date = (
        df_btc.index.max() - pd.DateOffset(months=investment_window)
    ).date()

    if max_start_date < min_start_date:
        st.error(f"Insufficient data for a {investment_window}-month window.")
        st.stop()

    # Set a default start date from user info or one year before today
    default_start = config.TODAY - pd.DateOffset(months=12)
    if st.session_state.get("user_info") and "start_date" in st.session_state.user_info:
        default_start = pd.to_datetime(st.session_state.user_info["start_date"])

    with col1:
        start_date_input = st.date_input(
            "Accumulation Start Date",
            value=default_start.date(),
            min_value=min_start_date,
            max_value=max_start_date,
            help="Choose when the accumulation period begins. Future dates are allowed.",
        )

    start_ts = pd.Timestamp(start_date_input)
    end_ts = start_ts + pd.DateOffset(months=investment_window)

    with col2:
        st.date_input(
            "Accumulation End Date",
            value=end_ts.date(),
            disabled=True,
            help=f"Automatically set to {investment_window} months after the start date.",
        )

    # --- DataFrame Window Extraction ---
    df_window = df_btc.loc[start_ts:end_ts].copy()
    if len(df_window) < 30:
        st.warning(
            "⚠️ Selected period has insufficient data. Please choose another date."
        )
        st.stop()

    # --- State Management & Simulation Day Logic ---
    today_is_in_window = start_ts <= config.TODAY <= end_ts
    today_day_index = None
    if today_is_in_window:
        try:
            # Use get_loc for a robust way to find the integer position of TODAY
            today_day_index = df_window.index.get_loc(config.TODAY)
        except KeyError:
            # TODAY might not align perfectly with an index if data is missing
            today_is_in_window = False
            print(
                "Info: Today is within the date range, but not a valid index in df_window."
            )

    # Reset simulation if the date window changes
    if (
        st.session_state.get("last_start_date") != start_ts
        or st.session_state.get("last_investment_window") != investment_window
    ):

        st.session_state.current_day = (
            today_day_index if today_day_index is not None else 0
        )
        st.session_state.last_start_date = start_ts
        st.session_state.last_investment_window = investment_window
        st.session_state.bayesian_history = []  # Reset learning on new window

    st.markdown("---")
    st.markdown("### Time Control")

    # --- Time Control Slider & Buttons (using 0-based index) ---
    max_day_index = len(df_window) - 1

    # Ensure current_day from state is within bounds
    st.session_state.current_day = min(
        st.session_state.get("current_day", 0), max_day_index
    )
    # print(st.session_state.current_day)

    # Main slider

    current_day = st.session_state.current_day

    # Buttons
    cols = st.columns(6 if today_is_in_window else 5)
    if cols[0].button("⏮️ First", width="stretch"):
        st.session_state.current_day = 0
        st.rerun()
    if cols[1].button("◀️ Prev", width="stretch"):
        st.session_state.current_day = max(0, st.session_state.current_day - 1)
        st.rerun()
    if cols[2].button("▶️ Next", width="stretch"):
        st.session_state.current_day = min(
            max_day_index, st.session_state.current_day + 1
        )
        st.rerun()
    if cols[3].button("⏭️ Last", width="stretch"):
        st.session_state.current_day = max_day_index
        st.rerun()
    if today_is_in_window and cols[4].button("📅 Today", width="stretch"):
        st.session_state.current_day = today_day_index
        st.rerun()

    st.slider(
        "Current Day in Period",
        min_value=0,
        max_value=max_day_index,
        value=st.session_state.current_day,
        key="current_day",  # Bind directly to session state
        help="Slide to simulate progression through the accumulation period (Day 0 is the start).",
    )

    st.markdown("---")

    return start_ts, current_day, df_window
