# ui/controls.py
import streamlit as st
import pandas as pd
import dashboard.config as config
from datetime import datetime
from dashboard.config import TODAY


def render_controls(df_btc, investment_window):
    """
    Renders date selection and time control panel.
    Returns start_date (Timestamp), current_day (0-based int), and df_window.
    """
    st.markdown("### 📅 Accumulation Period")

    # --- Date Selection ---
    min_start_date = df_btc.index.min().date()
    max_start_date = (TODAY - pd.DateOffset(days=1)).date()
    print("MAX START DATE", max_start_date)
    if max_start_date < min_start_date:
        st.error(f"Insufficient data for a {investment_window}-month window.")
        st.stop()
    print("TODAY:", config.TODAY)
    # Set a default start date from user info or one year before today
    default_start = config.TODAY - pd.DateOffset(months=investment_window)
    print("DEFAULT START:", default_start.date())
    if st.session_state.get("user_info") and "start_date" in st.session_state.user_info:
        default_start = pd.to_datetime(st.session_state.user_info["start_date"])
    print(default_start.date())

    start_ts = pd.Timestamp(default_start.date())
    end_ts = start_ts + pd.DateOffset(months=investment_window)

    today_is_in_window = start_ts <= config.TODAY <= end_ts
    today_day_index = None
    # --- DataFrame Window Extraction ---
    df_window = df_btc.loc[start_ts:end_ts].copy()
    if len(df_window) < 30:
        st.warning(
            "⚠️ Selected period has insufficient data. Please choose another date."
        )
        st.stop()

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

    # --- Time Control Slider & Buttons (using 0-based index) ---
    max_day_index = len(df_window) - 1

    # Ensure current_day from state is within bounds
    st.session_state.current_day = min(
        st.session_state.get("current_day", 0), max_day_index
    )

    current_day = st.session_state.current_day

    # Create all columns in one line - 2 date inputs + 4 buttons (+ 1 optional Today button)
    num_cols = 7 if today_is_in_window else 6
    cols = st.columns(num_cols)

    col_idx = 0

    # Start Date Input
    with cols[col_idx]:
        start_date_input = st.date_input(
            "Accumulation Start Date",
            value=default_start.date(),
            min_value=min_start_date,
            max_value=max_start_date,
            help="Choose when the accumulation period begins.",
        )

    col_idx += 1

    # End Date Input
    with cols[col_idx]:
        st.date_input(
            "Accumulation End Date",
            value=end_ts.date(),
            disabled=True,
            help=f"Automatically set to {investment_window} months after the start date.",
        )

    col_idx += 1

    # First Button
    if cols[col_idx].button("⏮️ First", use_container_width=True):
        st.session_state.current_day = 0
        st.rerun()

    col_idx += 1

    # Prev Button
    if cols[col_idx].button("◀️ Prev", use_container_width=True):
        st.session_state.current_day = max(0, st.session_state.current_day - 1)
        st.rerun()

    col_idx += 1

    # Next Button
    if cols[col_idx].button("▶️ Next", use_container_width=True):
        st.session_state.current_day = min(
            max_day_index, st.session_state.current_day + 1
        )
        st.rerun()

    col_idx += 1

    # Last Button
    if cols[col_idx].button("⏭️ Last", use_container_width=True):
        st.session_state.current_day = max_day_index
        st.rerun()

    # Today Button (conditional)
    if today_is_in_window:
        col_idx += 1
        if cols[col_idx].button("📅 Today", use_container_width=True):
            st.session_state.current_day = today_day_index
            st.rerun()

    # Update start_ts based on actual input
    start_ts = pd.Timestamp(start_date_input)
    end_ts = start_ts + pd.DateOffset(months=investment_window)
    df_window = df_btc.loc[start_ts:end_ts].copy()

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
