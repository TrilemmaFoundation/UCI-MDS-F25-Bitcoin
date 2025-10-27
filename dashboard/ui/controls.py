# dashboard/ui/controls.py
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
    if max_start_date < min_start_date:
        st.error(f"Insufficient data for a {investment_window}-month window.")
        st.stop()

    # Set a default start date from user info or one year before today
    default_start = config.TODAY - pd.DateOffset(months=investment_window)
    if st.session_state.get("user_info") and "start_date" in st.session_state.user_info:
        default_start = pd.to_datetime(st.session_state.user_info["start_date"])

    # Create all columns for date inputs and buttons first
    num_cols_temp = 7  # Max possible (will adjust later)
    widths = [2, 2, 1, 1, 1, 1, 1]
    cols = st.columns(widths)

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

    # Use the actual selected start date
    start_ts = pd.Timestamp(start_date_input)
    end_ts = start_ts + pd.DateOffset(months=investment_window)

    # End Date Input
    with cols[col_idx]:
        st.date_input(
            "Accumulation End Date",
            value=end_ts.date(),
            disabled=True,
            help=f"Automatically set to {investment_window} months after the start date.",
        )
    col_idx += 1

    # --- DataFrame Window Extraction ---
    # Get historical data up to the end date (or today if end_ts is in future)
    last_historical_date = df_btc[df_btc["Type"] == "Historical"].index.max()
    historical_end = min(end_ts, last_historical_date)

    df_window = df_btc.loc[start_ts:historical_end].copy()

    if len(df_window) < 30:
        st.warning(
            "⚠️ Selected period has insufficient data. Please choose another date."
        )
        st.stop()

    # --- Add Future Dates if Needed ---
    if end_ts > last_historical_date:
        # Calculate how many future days we need
        future_start = last_historical_date + pd.Timedelta(days=1)

        # Create future date range
        future_dates = pd.date_range(start=future_start, end=end_ts, freq="D")

        # Create placeholder future data with last known price
        last_price = df_window["PriceUSD"].iloc[-1]
        future_df = pd.DataFrame(
            {
                "PriceUSD": [last_price] * len(future_dates),
                "Type": ["Future"] * len(future_dates),
            },
            index=future_dates,
        )

        # Append future data to df_window
        df_window = pd.concat([df_window, future_df])

        st.info(
            f"ℹ️ Investment period extends {len(future_dates)} days into the future. Budget will be allocated across the entire {investment_window}-month period."
        )

    # Check if today is in the window
    today_is_in_window = start_ts <= config.TODAY <= end_ts
    today_day_index = None

    if today_is_in_window:
        try:
            # Use get_loc for a robust way to find the integer position of TODAY
            today_day_index = df_window.index.get_loc(config.TODAY)
        except KeyError:
            # TODAY might not align perfectly with an index if data is missing
            # Find the nearest date
            if config.TODAY in df_window.index:
                today_day_index = df_window.index.get_loc(config.TODAY)
            else:
                # Find closest date to today
                closest_date = df_window.index[df_window.index <= config.TODAY][-1]
                today_day_index = df_window.index.get_loc(closest_date)
                today_is_in_window = True

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

    # --- Time Control Buttons (using 0-based index) ---
    max_day_index = len(df_window) - 1

    # --- MODIFICATION START ---
    # Determine the max value for the slider to prevent going into the future
    slider_max_day = max_day_index
    if today_is_in_window and today_day_index is not None:
        slider_max_day = today_day_index
    elif start_ts > config.TODAY:  # If the whole window is in the future
        slider_max_day = 0

    # Ensure current_day from state is within the new, restricted bounds
    st.session_state.current_day = min(
        st.session_state.get("current_day", 0), slider_max_day
    )
    # --- MODIFICATION END ---

    current_day = st.session_state.current_day

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

    # Next Button - Use slider_max_day to cap navigation
    if cols[col_idx].button("▶️ Next", use_container_width=True):
        st.session_state.current_day = min(
            slider_max_day, st.session_state.current_day + 1
        )
        st.rerun()
    col_idx += 1

    # Last Button - Use slider_max_day to cap navigation
    if cols[col_idx].button("⏭️ Last", use_container_width=True):
        st.session_state.current_day = slider_max_day
        st.rerun()
    col_idx += 1

    # Today Button (conditional)
    if today_is_in_window and today_day_index is not None:
        if cols[col_idx].button("📅 Today", use_container_width=True):
            st.session_state.current_day = today_day_index
            st.rerun()

    st.slider(
        "Current Day in Period",
        min_value=0,
        max_value=slider_max_day,  # Use the calculated max day
        value=st.session_state.current_day,
        key="current_day",  # Bind directly to session state
        help="Slide to simulate progression through the accumulation period (Day 0 is the start).",
    )

    st.markdown("---")

    return start_ts, current_day, df_window
