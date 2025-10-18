# ui/controls.py
import streamlit as st
import pandas as pd
import dashboard.config as config
from datetime import datetime


def render_controls(df_btc, investment_window):
    """Renders date selection and time control panel, returns start_date and current_day."""
    st.markdown("### 📅 Select Accumulation Period")
    col1, col2 = st.columns(2)

    # The full data range now includes the forecast
    full_data_end_date = df_btc.index[-1]
    # Dynamically calculate the latest possible start date based on the full range
    max_start = (
        full_data_end_date
        - pd.DateOffset(months=investment_window)
        + pd.DateOffset(days=1)
    )

    with col1:
        min_start = df_btc.index[0]

        if max_start <= min_start:
            st.error(
                f"⚠️ Insufficient data for a {investment_window}-month window. "
                "Please choose a shorter investment window."
            )
            st.stop()

        # Set a reasonable default start date (e.g., today)
        default_start_date = config.today_raw - pd.DateOffset(months=12)

        default_start = max(min_start, default_start_date)

        if st.session_state.user_info != {}:
            default_start = datetime.strptime(
                st.session_state.user_info["start_date"], "%Y-%m-%d"
            )

        start_date = st.date_input(
            "Accumulation Start Date",
            value=default_start.date(),
            min_value=min_start.date(),
            max_value=max_start.date(),
            help=f"Choose when to start the {investment_window}-month accumulation period. Future dates are allowed.",
        )

    with col2:
        end_date = pd.Timestamp(start_date) + pd.DateOffset(months=investment_window)
        st.date_input(
            "Accumulation End Date",
            value=end_date.date(),
            disabled=True,
            help=f"Automatically set to {investment_window} months after start date",
        )

    # Extract window and check for validity
    start_ts = pd.Timestamp(start_date)
    end_ts = start_ts + pd.DateOffset(months=investment_window)

    try:
        df_window = df_btc.loc[start_ts:end_ts].copy()
    except Exception as e:
        st.error(f"Error extracting date range: {e}")
        st.stop()

    if len(df_window) < 30:
        st.warning(
            "⚠️ Selected period has insufficient data. Please choose a different date."
        )
        st.stop()

    # Reset simulation if start date OR investment window changes
    if (
        "current_day" not in st.session_state
        or st.session_state.get("last_start_date") != start_date
        or st.session_state.get("last_investment_window") != investment_window
    ):
        st.session_state.current_day = 1
        st.session_state.last_start_date = start_date
        st.session_state.last_investment_window = (
            investment_window  # Store current value
        )
        st.session_state.prior_mean = 0.0
        st.session_state.prior_var = 1.0
        st.session_state.bayesian_history = []

    st.markdown("---")

    # Time Control PanelF
    st.markdown("### Time Control")

    # Check if today falls within the window
    today = config.today_raw
    window_contains_today = start_ts <= today <= end_ts

    # Calculate which day index corresponds to today if applicable
    today_day_index = None
    if window_contains_today:
        days_from_start = (today - start_ts).days
        if 1 <= days_from_start < len(df_window):
            today_day_index = days_from_start + 1

    default_current_day = min(st.session_state.current_day, len(df_window) - 1)
    if window_contains_today:
        default_current_day = today_day_index

    # Create columns based on whether "Today" button should be shown
    if window_contains_today and today_day_index is not None:
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
    else:
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    with col1:
        current_day = st.slider(
            "Current Day in Period",
            min_value=1,
            max_value=len(df_window) - 1,
            value=default_current_day,
            help="Slide to simulate progression through the accumulation period",
        )
        st.session_state.current_day = current_day
    with col2:
        if st.button("⏮️ First", use_container_width=True):
            st.session_state.current_day = 1
            st.rerun()
    with col3:
        if st.button("◀️ Prev", use_container_width=True):
            if st.session_state.current_day > 1:
                st.session_state.current_day -= 1
                st.rerun()
    with col4:
        if st.button("▶️ Next", use_container_width=True):
            if st.session_state.current_day < len(df_window) - 1:
                st.session_state.current_day += 1
                st.rerun()
    with col5:
        if st.button("⏭️ Last", use_container_width=True):
            st.session_state.current_day = len(df_window) - 1
            st.rerun()

    # Add "Today" button only if today is in the window
    if window_contains_today and today_day_index is not None:
        with col6:
            if st.button("📅 Today", use_container_width=True):
                st.session_state.current_day = today_day_index
                st.rerun()
    st.markdown("---")

    return start_date, current_day, df_window
