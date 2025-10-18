# Dashboard.py
import streamlit as st
import pandas as pd
import sys

print()

# --- Local Imports ---
sys.path.append(".")
from dashboard.model.strategy_new import compute_weights
from dashboard.model.strategy_gt import compute_weights as compute_weights_gt
from dashboard.sidebar import render_sidebar

import dashboard.config as config
from dashboard.data_loader import load_bitcoin_data
from dashboard.simulation import (
    update_bayesian_belief,
    simulate_accumulation,
    calculate_uniform_dca_performance,
)
from dashboard.ui.header import render_header
from dashboard.ui.controls import render_controls
from dashboard.ui.validation import render_validation
from dashboard.ui.performance_tabs import render_performance
from dashboard.ui.recommendations import render_recommendations


def main():
    st.set_page_config(
        page_title="BTC Accumulation Dashboard",
        layout="wide",
        page_icon="₿",
        initial_sidebar_state="expanded",
    )

    # --- Sidebar and Parameters ---
    params = render_sidebar()

    # --- Data Loading ---
    with st.spinner("📥 Loading Bitcoin price data and generating forecast..."):
        df_btc = load_bitcoin_data()
    if df_btc is None or df_btc.empty:
        st.error("❌ Unable to load Bitcoin data. Please check and try again.")
        st.stop()

    # --- UI Rendering: Header and Controls ---
    render_header(df_btc[df_btc["Type"] == "Historical"], config.today_formatted)
    start_date, current_day, df_window = render_controls(
        df_btc, params["investment_window"]
    )

    # --- Core Logic: Strategy Calculation ---
    model_choice = params.get("model_choice", "Current Model")
    
    with st.spinner(f"🧮 Computing dynamic weights using {model_choice}..."):
        if model_choice == "GT-MSA-S25-Trilemma Model":
            weights = compute_weights_gt(df_window)
        else:
            weights = compute_weights(df_window, boost_alpha=params["boost_alpha"])

    dynamic_perf = simulate_accumulation(
        df_window, weights, params["budget"], current_day
    )
    uniform_perf = calculate_uniform_dca_performance(
        df_window, params["budget"], current_day
    )

    # --- UI Rendering: Validation and Performance ---
    # render_validation(weights, dynamic_perf, params["budget"], current_day)

    # --- Bayesian Update Logic ---
    if current_day >= 7:
        df_for_learning = df_window.iloc[max(0, current_day - 6) : current_day + 1]
        df_for_learning = df_for_learning[df_for_learning["Type"] == "Historical"]

        if len(df_for_learning) > 1:
            recent_return = df_for_learning["PriceUSD"].pct_change().mean()
            obs_var = df_for_learning["PriceUSD"].pct_change().var()

            if obs_var > 0:
                # Ensure prior parameters exist in session state
                if "prior_mean" not in st.session_state:
                    st.session_state.prior_mean = 0.0
                if "prior_var" not in st.session_state:
                    st.session_state.prior_var = 1.0
                    
                new_mean, new_var = update_bayesian_belief(
                    st.session_state.prior_mean,
                    st.session_state.prior_var,
                    recent_return,
                    obs_var,
                )
                # Ensure bayesian_history exists and is initialized
                if "bayesian_history" not in st.session_state:
                    st.session_state.bayesian_history = []
                    
                if (
                    not st.session_state.bayesian_history
                    or st.session_state.bayesian_history[-1]["day"] != current_day
                ):
                    st.session_state.bayesian_history.append(
                        {
                            "day": current_day,
                            "mean": new_mean,
                            "var": new_var,
                            "confidence": 1 / new_var,
                        }
                    )
                    st.session_state.prior_mean, st.session_state.prior_var = (
                        new_mean,
                        new_var,
                    )

    # --- Prepare data for charts and pass to rendering functions ---
    df_current = df_window.iloc[: current_day + 1]

    # NEW: Create the extended DataFrame for chart display
    window_start_date = df_window.index[0]
    historical_context_start_date = window_start_date - pd.DateOffset(years=1)
    current_view_end_date = df_current.index[-1]

    # Ensure the start date is not before the beginning of all available data
    chart_display_start = max(historical_context_start_date, df_btc.index[0])
    df_for_chart = df_btc.loc[chart_display_start:current_view_end_date].copy()

    render_recommendations(
        dynamic_perf,
        df_current,
        weights,
        params["budget"],
        current_day,
        start_date + pd.DateOffset(days=current_day),
    )

    render_performance(
        df_window=df_window,
        weights=weights,
        dynamic_perf=dynamic_perf,
        uniform_perf=uniform_perf,
        current_day=current_day,
        df_for_chart=df_for_chart,  # Pass the new extended DataFrame
        model_choice=model_choice,  # Pass model choice
    )

    st.info(
        f"**Note:** Price data after **{config.HISTORICAL_END}** is a simulation "
        "for forward-looking analysis and is not a financial prediction."
    )


if __name__ == "__main__":
    main()
