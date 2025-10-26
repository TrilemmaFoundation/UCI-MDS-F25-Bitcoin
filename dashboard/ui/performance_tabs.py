# ui/performance_tabs.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar as cal_module
from dashboard.ui.charts import (
    render_price_signals_chart,
    render_weight_distribution_chart,
    render_bayesian_learning_chart,
    render_strategy_comparison_chart,
)
from dashboard.model.strategy_new import construct_features
from dashboard.analytics.portfolio_metrics import PortfolioAnalyzer, compare_strategies

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
    Renders key metrics and the main tab layout for visualizations.
    Accepts an additional df_for_chart for historical context.
    """
    metrics = _calculate_metrics(df_window, dynamic_perf, uniform_perf, current_day)

    if model_choice:
        if model_choice == "GT-MSA-S25-Trilemma Model":
            st.success(
                "🎯 **Using GT-MSA-S25-Trilemma Model** - Final Score: 94.5% | Win Rate: 99.4%"
            )
        else:
            st.info(f"📊 **Using {model_choice}**")

    current_price = df_window.iloc[current_day]["PriceUSD"]
    dynamic_btc = dynamic_perf.iloc[-1]["Total_BTC"]
    uniform_btc = uniform_perf.iloc[-1]["Total_BTC"]
    btc_advantage = (
        ((dynamic_btc - uniform_btc) / uniform_btc * 100) if uniform_btc > 0 else 0
    )
    dynamic_pnl_pct = dynamic_perf.iloc[-1]["PnL_Pct"]
    dynamic_spd = dynamic_perf.iloc[-1]["Cumulative_SPD"]
    uniform_spd = uniform_perf.iloc[-1]["Cumulative_SPD"]
    spd_advantage = (
        ((dynamic_spd - uniform_spd) / uniform_spd * 100) if uniform_spd > 0 else 0
    )
    current_date = str(df_window.index[current_day] - pd.DateOffset(days=1))[:10]
    metrics_data = {
        "Metric": [
            f"{current_date} BTC Price",
            "Total BTC (Dynamic)",
            "Portfolio Value",
            "Profit / Loss",
            "SPD Performance",
        ],
        "Value": [
            f"${current_price:,.0f}",
            f"{dynamic_btc:.5f} ₿",
            f"${dynamic_perf.iloc[-1]['Portfolio_Value']:,.2f}",
            f"${dynamic_perf.iloc[-1]['PnL']:,.2f}",
            f"{dynamic_spd:,.0f}",
        ],
        "Change / Comparison": [
            "",
            f"+{btc_advantage:.2f}% vs DCA",
            "",
            f"{dynamic_pnl_pct:+.2f}%",
            f"+{spd_advantage:.2f}% vs DCA",
        ],
    }

    tab1, tab2, tab3 = st.tabs(
        [
            "📈 Price & Signals",
            "📊 Strategy Comparison",
            "🎯 Risk Metrics",
        ]
    )

    df_current = df_window.iloc[: current_day + 1]

    with tab1:
        render_price_signals_chart(
            df_chart_display=df_for_chart,
            weights=weights,
            df_window=df_window,
            current_day=current_day,
        )

    # with tab2:
    #     df_current_slice = df_window.iloc[: current_day + 1]
    #     render_weight_distribution_chart(weights, df_current_slice)

    with tab2:
        st.markdown("### Cumulative Sats-per-Dollar (SPD) Comparison")
        st.info(
            "Higher SPD means you are accumulating more Bitcoin for every dollar spent."
        )
        render_strategy_comparison_chart(dynamic_perf, uniform_perf)
        st.markdown("---")
        render_comparison_summary(metrics, dynamic_perf, uniform_perf)

    # with tab3:
    #     render_purchasing_calendar(df_current, dynamic_perf, weights, current_day)

    with tab3:
        render_risk_metrics_tab(dynamic_perf, uniform_perf)

    st.markdown("<h3>Performance Metrics</h3>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(metrics_data), hide_index=True)
    st.markdown("---")


def render_risk_metrics_tab(dynamic_perf, uniform_perf):
    """Render Risk Metrics Tab with advanced analytics"""
    st.markdown("### 📊 Advanced Risk & Performance Metrics")

    analyzer_dynamic = PortfolioAnalyzer(dynamic_perf)
    analyzer_uniform = PortfolioAnalyzer(uniform_perf)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sharpe = analyzer_dynamic.sharpe_ratio()
        st.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}",
            help="Risk-adjusted returns (>1 is good, >2 is excellent)",
        )

    with col2:
        sortino = analyzer_dynamic.sortino_ratio()
        st.metric(
            "Sortino Ratio",
            f"{sortino:.2f}",
            help="Downside risk-adjusted returns (higher is better)",
        )

    with col3:
        max_dd, _, _ = analyzer_dynamic.max_drawdown()
        st.metric(
            "Max Drawdown",
            f"{max_dd:.2f}%",
            delta=f"{max_dd:.2f}%",
            delta_color="inverse",
            help="Largest peak-to-trough decline (lower is better)",
        )

    with col4:
        win_rate = analyzer_dynamic.win_rate()
        st.metric("Win Rate", f"{win_rate:.1f}%", help="Percentage of profitable days")

    st.markdown("---")

    st.markdown("### 📋 Strategy Comparison Table")
    comparison_df = compare_strategies(dynamic_perf, uniform_perf)

    # FIX: Use Streamlit's format parameter to prevent the FutureWarning
    # This applies the specified format to all numeric columns for display
    # purposes without changing the underlying data types.
    st.dataframe(
        comparison_df.style.format("{:.2f}", na_rep=""),
    )

    st.markdown("### 📈 Risk-Return Profile")

    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[analyzer_dynamic.volatility() * 100],
            y=[dynamic_perf.iloc[-1]["PnL_Pct"]],
            mode="markers",
            name="Dynamic Strategy",
            marker=dict(size=20, color="#667eea"),
            text=["Dynamic Strategy"],
            hovertemplate="<b>%{text}</b><br>Risk: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[analyzer_uniform.volatility() * 100],
            y=[uniform_perf.iloc[-1]["PnL_Pct"]],
            mode="markers",
            name="Uniform DCA",
            marker=dict(size=20, color="#f7931a"),
            text=["Uniform DCA"],
            hovertemplate="<b>%{text}</b><br>Risk: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Risk vs Return",
        xaxis_title="Volatility (Risk) %",
        yaxis_title="Total Return %",
        height=400,
    )

    st.plotly_chart(fig, config={"displayModeBar": True})

    with st.expander("ℹ️ Understanding Risk Metrics"):
        st.markdown(
            """
        **Sharpe Ratio**: Measures return per unit of risk. Higher is better.
        - < 1: Poor risk-adjusted returns
        - 1-2: Good performance
        - > 2: Excellent performance

        **Sortino Ratio**: Like Sharpe, but only penalizes downside volatility.
        - Focuses on harmful volatility (losses)
        - Higher values indicate better downside protection

        **Max Drawdown**: Largest peak-to-trough loss. Lower is better.
        - Shows worst-case scenario
        - Important for understanding potential losses

        **Win Rate**: % of days with positive returns.
        - Higher win rate = more consistent gains
        - Note: Can be misleading if wins are small and losses large

        **Calmar Ratio**: Annual return divided by max drawdown.
        - Higher values indicate better risk-adjusted returns
        - Useful for comparing strategies with different risk profiles

        **Volatility**: Standard deviation of returns (annualized).
        - Higher = more price swings
        - Lower = more stable returns
        """
        )


def render_purchasing_calendar(df_current, dynamic_perf, weights, current_day):
    """
    Render a calendar-style view of the purchasing schedule showing past days and current day only.
    Shows BTC price, buy indicators, and amount purchased for each day.
    """
    current_data = dynamic_perf.iloc[: current_day + 1].copy()

    if current_data.empty:
        st.info("No purchasing data available for the selected time period.")
        return

    try:
        features = construct_features(df_current)
    except Exception as e:
        st.error(f"Error constructing features: {e}")
        return
    st.markdown("---")
    st.markdown("### 📅 Daily Purchasing Schedule")
    st.markdown("*Daily investment plan details and analysis*")

    avg_weight = weights.mean() if len(weights) > 0 else 0

    start_date = current_data.iloc[0]["Date"]
    end_date = current_data.iloc[-1]["Date"]

    calendar_container = st.container()

    with calendar_container:
        current_data["YearMonth"] = current_data["Date"].dt.to_period("M")

        for period in sorted(current_data["YearMonth"].unique(), reverse=True):
            month_data = current_data[current_data["YearMonth"] == period]
            month_start = month_data.iloc[0]["Date"]
            with st.expander(month_start.strftime("%B %Y")):
                st.markdown(f"### {month_start.strftime('%B %Y')}")

                month_year = period.to_timestamp()
                first_day = month_year.replace(day=1)

                days_in_month = cal_module.monthrange(first_day.year, first_day.month)[
                    1
                ]
                first_weekday = first_day.weekday()

                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

                header_cols = st.columns(7)
                for i, day_name in enumerate(day_names):
                    with header_cols[i]:
                        st.markdown(f"**{day_name}**")

                total_cells = first_weekday + days_in_month
                num_weeks = (total_cells + 6) // 7

                for week in range(num_weeks):
                    cols = st.columns(7)
                    for day_of_week in range(7):
                        cell_num = week * 7 + day_of_week

                        with cols[day_of_week]:
                            if cell_num < first_weekday:
                                st.markdown("")
                            elif cell_num < first_weekday + days_in_month:
                                day_num = cell_num - first_weekday + 1
                                current_date = first_day.replace(day=day_num)

                                day_data = month_data[
                                    month_data["Date"].dt.date == current_date.date()
                                ]

                                if not day_data.empty:
                                    day_info = day_data.iloc[-1]

                                    price = day_info["Price"]
                                    amount_spent = day_info["Amount_Spent"]
                                    weight = day_info["Weight"]

                                    signal_style = _get_signal_style(weight, avg_weight)

                                    day_style = f"""
                                    <div style="
                                        border: 2px solid {signal_style['color']};
                                        border-radius: 8px;
                                        padding: 8px;
                                        margin: 2px;
                                        background-color: rgba(255,255,255,0.9);
                                        text-align: center;
                                        min-height: 80px;
                                    ">
                                        <div style="font-weight: bold; font-size: 14px;">
                                            {day_num}
                                        </div>
                                        <div style="font-size: 10px; color: {signal_style['color']}; margin: 2px 0;">
                                            {signal_style['emoji']} {signal_style['text']}
                                        </div>
                                        <div style="font-size: 9px; margin: 2px 0;">
                                            <strong>${price:,.0f}</strong>
                                        </div>
                                        <div style="font-size: 8px; color: #666;">
                                            ${amount_spent:.0f}
                                        </div>
                                    </div>
                                    """
                                    st.markdown(day_style, unsafe_allow_html=True)
                                else:
                                    if current_date.date() <= datetime.now().date():
                                        st.markdown(
                                            f"""
                                        <div style="
                                            border: 1px solid #ccc;
                                            border-radius: 8px;
                                            padding: 8px;
                                            margin: 2px;
                                            background-color: rgba(240,240,240,0.5);
                                            text-align: center;
                                            min-height: 80px;
                                        ">
                                            <div style="font-weight: bold; font-size: 14px;">
                                                {day_num}
                                            </div>
                                            <div style="font-size: 10px; color: #999; margin: 2px 0;">
                                                No Purchase
                                            </div>
                                        </div>
                                        """,
                                            unsafe_allow_html=True,
                                        )
                                    else:
                                        st.markdown("")
                            else:
                                st.markdown("")

        st.markdown("#### Legend")
        legend_cols = st.columns(5)
        with legend_cols[0]:
            st.markdown(
                "🟢 **Strong Buy**<br/>Price significantly below trend",
                unsafe_allow_html=True,
            )
        with legend_cols[1]:
            st.markdown(
                "🟠 **Moderate Buy**<br/>Price below trend", unsafe_allow_html=True
            )
        with legend_cols[2]:
            st.markdown(
                "🟡 **Light Buy**<br/>Slightly favorable conditions",
                unsafe_allow_html=True,
            )
        with legend_cols[3]:
            st.markdown(
                "🔴 **Reduced**<br/>Above trend, reduced allocation",
                unsafe_allow_html=True,
            )
        with legend_cols[4]:
            st.markdown("⚪ **Normal**<br/>Standard allocation", unsafe_allow_html=True)
