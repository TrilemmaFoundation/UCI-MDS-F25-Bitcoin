# dashboard/ui/controls.py
import streamlit as st
import pandas as pd
import dashboard.config as config
from datetime import datetime
from dashboard.config import get_today


def render_controls(df_btc, investment_window):
    """
    Renders date selection and time control panel.
    Returns start_date (Timestamp), current_day (0-based int), and df_window.
    """
    st.markdown("### 📅 Accumulation Period")

    # --- Date Selection ---
    min_start_date = df_btc.index.min().date()
    # Allow selecting dates well into the future
    max_start_date = (get_today()).date()

    # Set a default start date from user info or today
    default_start = config.get_today()
    if st.session_state.get("user_info") and "start_date" in st.session_state.user_info:
        default_start = pd.to_datetime(st.session_state.user_info["start_date"])

    # Create all columns for date inputs and buttons first
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
    # Get historical data up to the end date (or last available if end_ts is in future)
    last_historical_date = df_btc[df_btc["Type"] == "Historical"].index.max()

    # Determine the actual start for historical data
    # If start_ts is in the future, we'll start from the last historical date
    historical_start = max(start_ts, df_btc.index.min())
    historical_end = min(end_ts, last_historical_date)

    # Extract historical data that overlaps with our window
    if historical_start <= last_historical_date:
        df_window = df_btc.loc[historical_start:historical_end].copy()
    else:
        # Entire window is in the future - create empty DataFrame with correct structure
        df_window = pd.DataFrame(columns=["PriceUSD", "Type"])
        df_window.index.name = "time"

    # --- Add Future Dates if Needed ---
    # Calculate if we need future data
    future_needed = end_ts > last_historical_date

    if future_needed:
        # Determine where future data should start
        if start_ts > last_historical_date:
            # Entire window is in the future
            future_start = start_ts
            st.info(
                f"ℹ️ The selected investment period is entirely in the future. "
                f"Using last known BTC price (${df_btc['PriceUSD'].iloc[-1]:,.2f}) "
                f"for DCA schedule planning."
            )
        else:
            # Window spans historical and future
            future_start = last_historical_date + pd.Timedelta(days=1)
            future_days = (end_ts - future_start).days + 1
            st.info(
                f"ℹ️ Investment period extends {future_days} days into the future. "
                f"Budget will be allocated across the entire {investment_window}-month period."
            )

        # Create future date range
        future_dates = pd.date_range(start=future_start, end=end_ts, freq="D")

        # Get last known price for future projections
        last_price = df_btc["PriceUSD"].iloc[-1]

        # Create placeholder future data
        future_df = pd.DataFrame(
            {
                "PriceUSD": [last_price] * len(future_dates),
                "Type": ["Future"] * len(future_dates),
            },
            index=future_dates,
        )

        # Append future data to df_window
        df_window = pd.concat([df_window, future_df])

    # Final validation - ensure we have some data
    if len(df_window) < 1:
        st.error(
            "⚠️ Unable to create investment window. Please try a different date range."
        )
        st.stop()

    # Check if today is in the window
    today_is_in_window = start_ts <= config.get_today() <= end_ts
    today_day_index = None

    if today_is_in_window:
        try:
            # Use get_loc for a robust way to find the integer position of get_today()
            today_day_index = df_window.index.get_loc(config.get_today())
        except KeyError:
            # get_today() might not be in the index - find closest date
            if config.get_today() <= df_window.index[-1]:
                # Find closest date to today that's in our window
                valid_dates = df_window.index[df_window.index <= config.get_today()]
                if len(valid_dates) > 0:
                    closest_date = valid_dates[-1]
                    today_day_index = df_window.index.get_loc(closest_date)
                else:
                    today_is_in_window = False

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

    # Determine the max value for the slider to prevent going into the future
    slider_max_day = max_day_index
    if today_is_in_window and today_day_index is not None:
        slider_max_day = today_day_index
    elif start_ts > config.get_today():  # If the whole window is in the future
        slider_max_day = (
            max_day_index  # Allow viewing entire future window for planning
        )

    # Ensure current_day from state is within the new, restricted bounds
    st.session_state.current_day = min(
        st.session_state.get("current_day", 0), slider_max_day
    )

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

    if slider_max_day != 0:
        st.slider(
            "Current Day in Period",
            min_value=0,
            max_value=slider_max_day,
            # value=st.session_state.current_day,
            key="current_day",  # Bind directly to session state
            help="Slide to simulate progression through the accumulation period (Day 0 is the start).",
        )

    st.markdown("---")

    return start_ts, current_day, df_window
