# dashboard/Daily_Schedule.py
import streamlit as st
import pandas as pd
import sys

sys.path.append(".")

# --- Local Imports ---
import dashboard.config as config
from dashboard.data_loader import load_bitcoin_data
from dashboard.model.strategy_new import compute_weights
from dashboard.model.strategy_gt import (
    compute_weights as compute_weights_gt,
)  # Example for alternate model
from dashboard.sidebar_simplified import render_sidebar
from dashboard.simulation import (
    simulate_accumulation,
    calculate_uniform_dca_performance,
    update_bayesian_belief,
)
from dashboard.ui.header import render_header
from dashboard.ui.controls import render_controls
from dashboard.ui.performance_tabs import render_performance
from dashboard.ui.recommendations import render_recommendations
from dashboard.ui.performance_tabs import render_purchasing_calendar


def initialize_session_state():
    """Initialize all necessary session state variables if they don't exist."""
    defaults = {
        "current_day": 0,
        "prior_mean": 0.0,
        "prior_var": 1.0,
        "bayesian_history": [],
        "last_start_date": None,
        "last_investment_window": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def handle_bayesian_update(df_window: pd.DataFrame, current_day: int):
    """
    Performs a Bayesian belief update based on recent price returns.
    Updates are stored in st.session_state to persist across reruns.
    """
    # Start learning only after a week of data is available
    if current_day < 7:
        return

    # Check if we've already processed an update for this day
    if (
        st.session_state.bayesian_history
        and st.session_state.bayesian_history[-1]["day"] == current_day
    ):
        return

    # Use the last 7 days of historical (non-forecast) data for the update
    learning_slice = df_window.iloc[max(0, current_day - 6) : current_day + 1]
    learning_slice = learning_slice[learning_slice["Type"] == "Historical"]

    if len(learning_slice) > 1:
        returns = learning_slice["PriceUSD"].pct_change()
        recent_return_mean = returns.mean()
        obs_var = returns.var()

        # Update only if the observation variance is valid
        if pd.notna(obs_var) and obs_var > 0:
            new_mean, new_var = update_bayesian_belief(
                st.session_state.prior_mean,
                st.session_state.prior_var,
                recent_return_mean,
                obs_var,
            )

            # Store history and update the prior for the next iteration
            st.session_state.bayesian_history.append(
                {
                    "day": current_day,
                    "mean": new_mean,
                    "var": new_var,
                    "confidence": 1 / new_var,
                }
            )
            st.session_state.prior_mean, st.session_state.prior_var = new_mean, new_var


def main():
    """Main function to run the Streamlit dashboard application."""
    st.set_page_config(
        page_title="BTC Dynamic Accumulation Dashboard",
        layout="wide",
        page_icon="₿",
        initial_sidebar_state="expanded",
    )

    # --- 1. Initialization and Sidebar ---
    initialize_session_state()
    params = render_sidebar()

    # --- 2. Data Loading ---
    with st.spinner("📥 Loading Bitcoin price data..."):
        df_btc = load_bitcoin_data()
    if df_btc is None or df_btc.empty:
        st.error(
            "❌ Unable to load Bitcoin data. The API may be down. Please try again later."
        )
        st.stop()

    # --- 3. UI: Header and Controls ---
    render_header(df_btc[df_btc["Type"] == "Historical"], config.TODAY)
    start_date, current_day, df_window = render_controls(
        df_btc, params["investment_window"]
    )

    # --- NEW: Extend df_window with future dates if end date is in the future ---
    end_date = start_date + pd.DateOffset(days=params["investment_window"] - 1)
    last_historical_date = df_btc[df_btc["Type"] == "Historical"].index.max()

    if end_date > last_historical_date:
        # Calculate how many future days we need
        future_days_needed = (end_date - last_historical_date).days

        # Create future date range
        future_dates = pd.date_range(
            start=last_historical_date + pd.Timedelta(days=1),
            periods=future_days_needed,
            freq="D",
        )

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

    # --- 4. Core Computations ---
    print(df_window.head(5))
    print(df_window.tail(5))
    with st.spinner(f"🧮 Computing weights using {params['model_choice']}..."):
        if params["model_choice"] == "GT-MSA-S25-Trilemma Model":
            weights = compute_weights_gt(df_window)
        else:
            weights = compute_weights(df_window, boost_alpha=params["boost_alpha"])

    # Run simulations based on computed weights up to the selected day
    dynamic_perf = simulate_accumulation(
        df_window, weights, params["budget"], current_day
    )
    uniform_perf = calculate_uniform_dca_performance(
        df_window, params["budget"], current_day
    )

    # Perform Bayesian learning update (only on historical data)
    handle_bayesian_update(df_window, current_day)

    # --- 5. UI Rendering ---

    # Render the "Action Plan" for the current day
    render_recommendations(
        dynamic_perf=dynamic_perf,
        df_current=df_window,
        weights=weights,
        budget=params["budget"],
        current_day=current_day,
    )

    # Prepare a single, consistent DataFrame for charting that includes historical context
    chart_start_date = df_window.index.min() - pd.DateOffset(years=1)
    chart_end_date = df_window.index.max()
    df_chart_display = df_btc.loc[chart_start_date:chart_end_date].copy()

    # Render all performance tabs (Portfolio, Charts, etc.)
    render_purchasing_calendar(df_window, dynamic_perf, weights, current_day)


if __name__ == "__main__":
    main()
