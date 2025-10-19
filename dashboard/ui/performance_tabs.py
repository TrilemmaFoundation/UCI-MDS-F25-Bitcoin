# ui/performance_tabs.py
import streamlit as st
import pandas as pd
from dashboard.ui.charts import (
    render_price_signals_chart,
    render_weight_distribution_chart,
    render_bayesian_learning_chart,
    render_strategy_comparison_chart,
)

# --- Helper Functions for Calculation and Styling ---


def _calculate_metrics(df_window, dynamic_perf, uniform_perf, current_day):
    """Calculates all key performance indicators and returns them in a dictionary."""
    metrics = {}

    # Ensure there is performance data to process
    if dynamic_perf.empty or uniform_perf.empty:
        return {}

    last_day_dynamic = dynamic_perf.iloc[-1]
    last_day_uniform = uniform_perf.iloc[-1]

    # Core metrics
    metrics["current_price"] = df_window.iloc[current_day]["PriceUSD"]
    metrics["portfolio_value"] = last_day_dynamic["Portfolio_Value"]
    metrics["pnl"] = last_day_dynamic["PnL"]
    metrics["pnl_pct"] = last_day_dynamic["PnL_Pct"]
    metrics["dynamic_btc"] = last_day_dynamic["Total_BTC"]
    metrics["uniform_btc"] = last_day_uniform["Total_BTC"]
    metrics["dynamic_spd"] = last_day_dynamic["Cumulative_SPD"]
    metrics["uniform_spd"] = last_day_uniform["Cumulative_SPD"]

    # Comparison metrics
    metrics["btc_advantage_pct"] = (
        (metrics["dynamic_btc"] - metrics["uniform_btc"]) / metrics["uniform_btc"] * 100
        if metrics["uniform_btc"] > 0
        else 0
    )
    metrics["spd_advantage_pct"] = (
        (metrics["dynamic_spd"] - metrics["uniform_spd"]) / metrics["uniform_spd"] * 100
        if metrics["uniform_spd"] > 0
        else 0
    )

    return metrics


def _get_signal_style(weight: float, avg_weight: float) -> dict:
    """Returns a dictionary with style elements based on buy signal strength."""
    if weight > avg_weight * 2:
        return {"color": "green", "emoji": "🟢", "text": "Strong Buy"}
    elif weight > avg_weight * 1.5:
        return {"color": "#FFA500", "emoji": "🟠", "text": "Moderate Buy"}
    elif weight > avg_weight:
        return {"color": "#FFD700", "emoji": "🟡", "text": "Light Buy"}
    else:
        return {"color": "red", "emoji": "🔴", "text": "Reduced"}


# --- Main Rendering Functions ---


def render_main_metrics(metrics: dict):
    """Renders the main performance metrics using st.metric."""
    st.markdown("<h3>Portfolio Performance</h3>", unsafe_allow_html=True)

    if not metrics:
        st.warning("Not enough data to calculate performance metrics.")
        return

    cols = st.columns(4)
    cols[0].metric(
        "Portfolio Value",
        f"${metrics['portfolio_value']:,.2f}",
        f"{metrics['pnl_pct']:+.2f}% P&L",
    )
    cols[1].metric(
        "Total BTC Accumulated",
        f"{metrics['dynamic_btc']:.6f} ₿",
        f"{metrics['btc_advantage_pct']:+.2f}% vs. Uniform DCA",
    )
    cols[2].metric(
        "Sats-per-Dollar (SPD)",
        f"{metrics['dynamic_spd']:,.0f}",
        f"{metrics['spd_advantage_pct']:+.2f}% vs. Uniform DCA",
    )
    cols[3].metric("Current Bitcoin Price", f"${metrics['current_price']:,.2f}")
    st.markdown("---")


def render_comparison_summary(metrics: dict, dynamic_perf, uniform_perf):
    """Renders the summary tables for the strategy comparison tab."""
    st.markdown("#### Performance Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Dynamic Strategy**")
        st.markdown(
            f"""
            - **Total BTC:** `{metrics['dynamic_btc']:.8f} ₿`
            - **Avg. Entry:** `${dynamic_perf.iloc[-1]['Avg_Entry_Price']:,.2f}`
            - **P&L:** `${metrics['pnl']:,.2f} ({metrics['pnl_pct']:+.2f}%)`
            """
        )
    with col2:
        st.markdown("**Uniform DCA**")
        st.markdown(
            f"""
            - **Total BTC:** `{metrics['uniform_btc']:.8f} ₿`
            - **Avg. Entry:** `${uniform_perf.iloc[-1]['Avg_Entry_Price']:,.2f}`
            - **P&L:** `${uniform_perf.iloc[-1]['PnL']:,.2f} ({uniform_perf.iloc[-1]['PnL_Pct']:+.2f}%)`
            """
        )


def render_purchasing_calendar(dynamic_perf, weights):
    """Renders a simplified, list-style calendar of the purchasing schedule."""
    st.markdown("### 📅 Daily Purchasing Log")

    if dynamic_perf.empty:
        st.info("The accumulation period has not yet started.")
        return

    avg_weight = weights.mean() if not weights.empty else 0

    # Group data by month for a cleaner layout
    calendar_data = dynamic_perf.copy()
    calendar_data["YearMonth"] = calendar_data["Date"].dt.to_period("M")

    for period in sorted(calendar_data["YearMonth"].unique(), reverse=True):
        month_data = calendar_data[calendar_data["YearMonth"] == period]
        month_name = period.strftime("%B %Y")

        with st.expander(
            f"**{month_name}**",
            expanded=(period == calendar_data["YearMonth"].iloc[-1]),
        ):
            for _, day_info in month_data.iterrows():
                style = _get_signal_style(day_info["Weight"], avg_weight)
                cols = st.columns([1, 2, 2, 2, 3])

                cols[0].markdown(f"**{day_info['Date'].day}**")
                cols[1].markdown(f"**${day_info['Amount_Spent']:,.2f}**")
                cols[2].markdown(f"₿ {day_info['BTC_Bought']:.7f}")
                cols[3].markdown(f"@{day_info['Price']:,.2f}")
                cols[4].markdown(
                    f"<span style='color:{style['color']};'>{style['emoji']} {style['text']}</span>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)


def render_performance(
    df_window,
    weights,
    dynamic_perf,
    uniform_perf,
    current_day,
    df_for_chart,
    model_choice,
):
    """
    Renders key metrics and the main tab layout for all performance visualizations.
    """
    # 1. Calculate and Display Top-Level Metrics
    metrics = _calculate_metrics(df_window, dynamic_perf, uniform_perf, current_day)
    render_main_metrics(metrics)

    # 2. Setup and Render Tabs
    tab_titles = [
        "📈 Price & Signals",
        "⚖️ Weight Distribution",
        "📊 Strategy Comparison",
        "📅 Purchasing Log",
    ]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        render_price_signals_chart(
            df_chart_display=df_for_chart,
            weights=weights,
            df_window=df_window,
            current_day=current_day,
        )

    with tab2:
        df_current_slice = df_window.iloc[: current_day + 1]
        render_weight_distribution_chart(weights, df_current_slice)

    with tab3:
        st.markdown("### Cumulative Sats-per-Dollar (SPD) Comparison")
        st.info(
            "Higher SPD means you are accumulating more Bitcoin for every dollar spent."
        )
        render_strategy_comparison_chart(dynamic_perf, uniform_perf)
        st.markdown("---")
        render_comparison_summary(metrics, dynamic_perf, uniform_perf)

    with tab4:
        render_purchasing_calendar(dynamic_perf, weights)
