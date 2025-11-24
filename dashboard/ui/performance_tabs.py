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

from dashboard.config import get_today

from dashboard.model.strategy_new import construct_features
from dashboard.analytics.portfolio_metrics import PortfolioAnalyzer, compare_strategies
from dashboard.analytics.accumulation_metrics import AccumulationAnalyzer

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
    budget,
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
    current_date = df_window.index[current_day]

    # --- SPD Percentile Calculation ---
    historical_perf = dynamic_perf.iloc[: current_day + 1]
    if not historical_perf.empty:
        # Calculate theoretical best and worst SPD
        # Best case: buy all at the lowest price in the period
        # Worst case: buy all at the highest price in the period
        prices = df_window.iloc[: current_day + 1]["PriceUSD"]

        best_spd = (1e8 / prices.min()) * (current_day + 1)  # All buys at lowest price
        worst_spd = (1e8 / prices.max()) * (
            current_day + 1
        )  # All buys at highest price
        current_spd = historical_perf.iloc[-1]["Cumulative_SPD"]

        # Avoid division by zero
        if (best_spd - worst_spd) == 0:
            spd_percentile = 100.0
        else:
            spd_percentile = ((current_spd - worst_spd) / (best_spd - worst_spd)) * 100
    else:
        spd_percentile = 0.0  # Default value if there's no performance data

    metrics_data = {
        "Metric": [
            f"{current_date.strftime('%Y-%m-%d')} BTC Price",
            "Total BTC (Dynamic)",
            "Portfolio Value",
            "Profit / Loss",
            "SPD (Satoshis Per Dollar)",
            "SPD Percentile",
        ],
        "Value": [
            f"${current_price:,.0f}",
            f"{dynamic_btc:.5f} ₿",
            f"${dynamic_perf.iloc[-1]['Portfolio_Value']:,.2f}",
            f"${dynamic_perf.iloc[-1]['PnL']:,.2f}",
            f"{dynamic_spd:,.0f}",
            f"{spd_percentile:.1f}%",
        ],
        "Change / Comparison": [
            "",
            f"+{btc_advantage:.2f}% vs DCA",
            "",
            f"{dynamic_pnl_pct:+.2f}%",
            f"+{spd_advantage:.2f}% vs DCA",
            "Ranking vs historical performance",
        ],
    }

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📈 Price & Signals",
            "📊 Strategy Comparison",
            "💎 Performance Analytics",
            "📅 Purchasing Schedule",
            "🧠 Strategy Intelligence",
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

    with tab2:
        st.markdown("### Cumulative Sats-per-Dollar (SPD) Comparison")
        st.info(
            "Higher SPD means you are accumulating more Bitcoin for every dollar spent."
        )
        render_strategy_comparison_chart(dynamic_perf, uniform_perf)
        st.markdown("---")
        render_comparison_summary(metrics, dynamic_perf, uniform_perf)

    with tab3:
        render_risk_metrics_tab(dynamic_perf, uniform_perf)

    with tab4:
        render_purchasing_calendar(
            df_window, dynamic_perf, weights, current_day, total_budget=budget
        )

    with tab5:
        render_strategy_intelligence_tab(dynamic_perf, uniform_perf, df_window)

    st.markdown("<h3>Performance Metrics</h3>", unsafe_allow_html=True)

    metrics_df = pd.DataFrame(metrics_data)
    st.dataframe(
        metrics_df,
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn(
                "Metric",
                help="Key performance indicators for your Bitcoin investment strategy",
                width="medium",
            ),
            "Value": st.column_config.TextColumn(
                "Value", help="Current values and holdings", width="medium"
            ),
            "Change / Comparison": st.column_config.TextColumn(
                "Change / Comparison",
                help="Performance comparison against uniform dollar-cost averaging (DCA) strategy. Positive percentages indicate the dynamic strategy is outperforming uniform DCA by accumulating more Bitcoin per dollar spent.",
                width="medium",
            ),
        },
        width="stretch",
    )

    # Add additional explanation for SPD
    with st.expander("ℹ️ What are SPD (Satoshis Per Dollar) and SPD Percentile?"):
        st.markdown(
            """
            **Satoshis Per Dollar (SPD)** measures the efficiency of your Bitcoin accumulation strategy.
            
            - **What it measures**: How many satoshis (the smallest unit of Bitcoin, 0.00000001 BTC) you acquire for each dollar invested.
            - **Why it matters**: Higher SPD means you're getting more Bitcoin for your money.
            - **SPD Percentile**: This shows how your current SPD ranks against its own historical performance within the selected timeframe. A value of 100% means your current purchasing efficiency is the best it has been.
            
            *Example*: If SPD is +15% vs DCA, you're accumulating 15% more Bitcoin for the same budget using the dynamic strategy.
            """
        )


def render_risk_metrics_tab(dynamic_perf, uniform_perf):
    """Render Performance Analytics Tab with institutional-grade metrics"""
    st.markdown("## 💎 Performance Analytics")
    st.markdown("*Institutional-grade metrics demonstrating strategy quality and consistency*")
    st.markdown("---")

    analyzer_dynamic = PortfolioAnalyzer(dynamic_perf)
    analyzer_uniform = PortfolioAnalyzer(uniform_perf)

    # Calculate all metrics
    sharpe = analyzer_dynamic.sharpe_ratio()
    sortino = analyzer_dynamic.sortino_ratio()
    max_dd, dd_start, dd_end = analyzer_dynamic.max_drawdown()
    win_rate = analyzer_dynamic.win_rate()
    volatility = analyzer_dynamic.volatility() * 100
    calmar = analyzer_dynamic.calmar_ratio()
    total_return = dynamic_perf.iloc[-1]["PnL_Pct"] if not dynamic_perf.empty else 0

    # Calculate performance grade
    def get_performance_grade(sharpe, sortino, win_rate):
        score = 0
        # Sharpe contribution
        if sharpe > 2: score += 40
        elif sharpe > 1: score += 25
        elif sharpe > 0: score += 10

        # Sortino contribution
        if sortino > 2: score += 40
        elif sortino > 1: score += 25
        elif sortino > 0: score += 10

        # Win rate contribution
        if win_rate > 70: score += 20
        elif win_rate > 50: score += 10

        if score >= 90: return "A+", "🟢", "#10b981"
        elif score >= 80: return "A", "🟢", "#10b981"
        elif score >= 70: return "B+", "🟡", "#f59e0b"
        elif score >= 60: return "B", "🟡", "#f59e0b"
        else: return "C", "🟠", "#f97316"

    grade, emoji, grade_color = get_performance_grade(sharpe, sortino, win_rate)

    # Section 1: Performance Grade Card
    st.markdown(f"""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, {grade_color} 0%, {grade_color}dd 100%);
                border-radius: 20px; color: white; margin-bottom: 20px;">
        <div style="font-size: 18px; opacity: 0.9; margin-bottom: 10px;">Strategy Performance Grade</div>
        <div style="font-size: 72px; font-weight: bold; margin: 15px 0;">
            {emoji} {grade}
        </div>
        <div style="font-size: 16px; opacity: 0.9;">
            {"Exceptional institutional-grade performance" if grade in ["A+", "A"] else
             "Strong risk-adjusted returns" if grade in ["B+", "B"] else
             "Room for parameter optimization"}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Section 2: Key Performance Metrics
    st.markdown("### 📊 Risk-Adjusted Performance Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sharpe_quality = "🟢 Excellent" if sharpe > 2 else "🟡 Good" if sharpe > 1 else "🟠 Fair"
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background: #f8fafc; border-radius: 10px; border: 2px solid #e2e8f0;">
            <div style="font-size: 12px; color: #64748b; margin-bottom: 5px;">SHARPE RATIO</div>
            <div style="font-size: 32px; font-weight: bold; color: #1e293b; margin: 10px 0;">
                {sharpe:.2f}
            </div>
            <div style="font-size: 13px; color: #475569;">{sharpe_quality}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        sortino_quality = "🟢 Excellent" if sortino > 2 else "🟡 Good" if sortino > 1 else "🟠 Fair"
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background: #f8fafc; border-radius: 10px; border: 2px solid #e2e8f0;">
            <div style="font-size: 12px; color: #64748b; margin-bottom: 5px;">SORTINO RATIO</div>
            <div style="font-size: 32px; font-weight: bold; color: #1e293b; margin: 10px 0;">
                {sortino:.2f}
            </div>
            <div style="font-size: 13px; color: #475569;">{sortino_quality}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        dd_quality = "🟢 Low" if abs(max_dd) < 10 else "🟡 Moderate" if abs(max_dd) < 20 else "🟠 High"
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background: #f8fafc; border-radius: 10px; border: 2px solid #e2e8f0;">
            <div style="font-size: 12px; color: #64748b; margin-bottom: 5px;">MAX DRAWDOWN</div>
            <div style="font-size: 32px; font-weight: bold; color: #1e293b; margin: 10px 0;">
                {abs(max_dd):.1f}%
            </div>
            <div style="font-size: 13px; color: #475569;">{dd_quality}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        wr_quality = "🟢 High" if win_rate > 70 else "🟡 Good" if win_rate > 50 else "🟠 Fair"
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background: #f8fafc; border-radius: 10px; border: 2px solid #e2e8f0;">
            <div style="font-size: 12px; color: #64748b; margin-bottom: 5px;">WIN RATE</div>
            <div style="font-size: 32px; font-weight: bold; color: #1e293b; margin: 10px 0;">
                {win_rate:.1f}%
            </div>
            <div style="font-size: 13px; color: #475569;">{wr_quality}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 3: Detailed Comparison
    st.markdown("### 📋 Strategy Performance Comparison")

    comparison_df = compare_strategies(dynamic_perf, uniform_perf)

    # Format the comparison table nicely
    st.dataframe(comparison_df.style.format("{:.2f}", na_rep=""), width="stretch")

    st.markdown("---")

    # Section 4: Risk-Return Visualization with Quadrants
    st.markdown("### 📈 Risk-Return Efficiency Map")
    st.info("Higher return with lower volatility indicates superior risk-adjusted performance")

    import plotly.graph_objects as go

    dynamic_vol = analyzer_dynamic.volatility() * 100
    dynamic_ret = total_return
    uniform_vol = analyzer_uniform.volatility() * 100
    uniform_ret = uniform_perf.iloc[-1]["PnL_Pct"] if not uniform_perf.empty else 0

    fig = go.Figure()

    # Add quadrant backgrounds
    avg_vol = (dynamic_vol + uniform_vol) / 2
    avg_ret = (dynamic_ret + uniform_ret) / 2

    # Add shaded regions
    fig.add_shape(type="rect", x0=0, y0=avg_ret, x1=avg_vol, y1=max(dynamic_ret, uniform_ret) * 1.2,
                  fillcolor="lightgreen", opacity=0.1, line_width=0)
    fig.add_annotation(x=avg_vol*0.5, y=max(dynamic_ret, uniform_ret) * 1.1,
                      text="🎯 Ideal Zone<br>(High Return, Low Risk)", showarrow=False,
                      font=dict(size=10, color="green"))

    # Plot strategies
    fig.add_trace(
        go.Scatter(
            x=[dynamic_vol],
            y=[dynamic_ret],
            mode="markers+text",
            name="Dynamic Strategy",
            marker=dict(size=25, color="#667eea", line=dict(width=2, color="white")),
            text=["Dynamic"],
            textposition="top center",
            textfont=dict(size=12, color="#667eea", family="Arial Black"),
            hovertemplate="<b>Dynamic Strategy</b><br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[uniform_vol],
            y=[uniform_ret],
            mode="markers+text",
            name="Uniform DCA",
            marker=dict(size=25, color="#f7931a", line=dict(width=2, color="white")),
            text=["Uniform DCA"],
            textposition="bottom center",
            textfont=dict(size=12, color="#f7931a", family="Arial Black"),
            hovertemplate="<b>Uniform DCA</b><br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        height=450,
        xaxis_title="Annualized Volatility (%)",
        yaxis_title="Total Return (%)",
        showlegend=False,
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, config={"displayModeBar": True}, width="stretch")

    # Performance interpretation
    if dynamic_ret > uniform_ret and dynamic_vol <= uniform_vol:
        st.success("🎯 **Superior Performance**: Your dynamic strategy delivers higher returns with equal or lower volatility - the ideal outcome for institutional investors.")
    elif dynamic_ret > uniform_ret:
        st.success(f"📈 **Outperforming**: Your strategy generates {dynamic_ret - uniform_ret:.1f}% higher returns. The slightly higher volatility is acceptable given the return premium.")
    else:
        st.info("📊 **Analysis**: Consider adjusting strategy parameters to improve risk-adjusted returns.")

    st.markdown("---")

    # Educational expander with positive framing
    with st.expander("ℹ️ Understanding Institutional Performance Metrics"):
        st.markdown(f"""
        ### Key Metrics Explained

        **Sharpe Ratio ({sharpe:.2f})**
        Measures return per unit of total risk. Your score of {sharpe:.2f} is {sharpe_quality.replace('🟢 ', '').replace('🟡 ', '').replace('🟠 ', '').lower()}.
        - **> 2.0**: Exceptional - Institutional quality
        - **1.0-2.0**: Good - Beating market averages
        - **< 1.0**: Fair - Room for optimization

        **Sortino Ratio ({sortino:.2f})**
        Like Sharpe, but focuses only on downside risk (more relevant for investors).
        - Measures how well you're being compensated for harmful volatility
        - Higher values mean better protection against losses

        **Maximum Drawdown ({abs(max_dd):.1f}%)**
        Largest peak-to-trough decline in portfolio value.
        - Shows resilience during market downturns
        - Lower drawdowns indicate more stable accumulation

        **Win Rate ({win_rate:.1f}%)**
        Percentage of days with positive portfolio value growth.
        - Indicates consistency of strategy
        - High win rates suggest systematic outperformance

        **Why These Metrics Matter**
        These are standard metrics used by:
        - Hedge funds evaluating trading strategies
        - Institutional investors assessing fund managers
        - Academic researchers validating systematic approaches

        Your Grade {emoji} **{grade}** reflects comprehensive evaluation across all dimensions.
        """
        )


def render_purchasing_calendar(
    df_current, dynamic_perf, weights, current_day, total_budget
):
    """
    Render a calendar-style view of the purchasing schedule showing past days and future planned DCA.
    Shows BTC price, buy indicators, and amount purchased/planned for each day.

    Args:
        df_current: DataFrame with price data
        dynamic_perf: Performance data up to current day
        weights: Weight array for signal strength
        current_day: Current day index (0-based)
        total_budget: Total budget for the investment period
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

    # Calculate remaining budget and days for future DCA
    total_spent = current_data["Amount_Spent"].sum()
    remaining_budget = total_budget - total_spent

    total_days = len(df_current)
    remaining_days = total_days - current_day - 1
    future_dca_amount = remaining_budget / remaining_days if remaining_days > 0 else 0

    start_date = df_current.index[0]
    end_date = start_date + pd.DateOffset(total_days - 1)

    # Get current date in Pacific timezone for comparison
    today_pacific = get_today()

    calendar_container = st.container()

    with calendar_container:
        # Create a combined view: historical + future
        all_dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # Group by month
        date_df = pd.DataFrame({"Date": all_dates})

        date_df["YearMonth"] = pd.to_datetime(date_df["Date"]).dt.to_period("M")
        for period in sorted(date_df["YearMonth"].unique()):
            month_dates = date_df[date_df["YearMonth"] == period]["Date"]
            month_start = month_dates.iloc[0]

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

                                # Check if this date is in our historical data
                                day_data = current_data[
                                    current_data["Date"].dt.date == current_date.date()
                                ]

                                if not day_data.empty:
                                    # Historical purchase
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
                                        <div style="font-weight: bold; color: #161B22; font-size: 14px;">
                                            {day_num}
                                        </div>
                                        <div style="font-size: 10px; color: {signal_style['color']}; margin: 2px 0;">
                                            {signal_style['emoji']} {signal_style['text']}
                                        </div>
                                        <div style="font-size: 20px; color: #161B22; margin: 2px 0;">
                                            <strong>${amount_spent:.0f}</strong>
                                        </div>
                                    </div>
                                    """
                                    st.markdown(day_style, unsafe_allow_html=True)
                                elif (
                                    current_date.date() > today_pacific.date()
                                    and current_date <= end_date
                                ):
                                    # Future planned DCA
                                    st.markdown(
                                        f"""
                                    <style>
                                        .dca-amount-{day_num} .hidden-amount {{
                                            opacity: 0;
                                            transition: opacity 0.2s ease;
                                        }}
                                        .dca-amount-{day_num} .placeholder {{
                                            opacity: 1;
                                            transition: opacity 0.2s ease;
                                        }}
                                        .dca-amount-{day_num}:hover .hidden-amount {{
                                            opacity: 1;
                                        }}
                                        .dca-amount-{day_num}:hover .placeholder {{
                                            opacity: 0;
                                        }}
                                    </style>
                                    <div style="
                                        border: 2px dashed #9CA3AF;
                                        border-radius: 8px;
                                        padding: 8px;
                                        margin: 2px;
                                        background-color: rgba(156,163,175,0.1);
                                        text-align: center;
                                        min-height: 80px;
                                    ">
                                        <div style="font-weight: bold; color: #fff; font-size: 14px;">
                                            {day_num}
                                        </div>
                                        <div style="font-size: 16px; color: #6B7280; margin: 2px 0;">
                                            ⏳
                                        </div>
                                        <div class="dca-amount-{day_num}" style="
                                            font-size: 16px; 
                                            color: #fff; 
                                            margin: 2px 0;
                                            position: relative;
                                            cursor: pointer;
                                        ">
                                            <strong class="hidden-amount">${future_dca_amount:.2f}</strong>
                                            <span class="placeholder" style="
                                                position: absolute;
                                                left: 50%;
                                                transform: translateX(-50%);
                                                top: 0;
                                            ">***</span>
                                        </div>
                                        <div style="font-size: 9px; color: #fff; margin: 2px 0;">
                                            Planned DCA
                                        </div>
                                    </div>
                                    """,
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    # Determine if this is a slider's current day to today's date (future relative to slider)
                                    slider_current_date = df_current.index[current_day]

                                    if (
                                        current_date.date() > slider_current_date.date()
                                        and current_date <= end_date
                                    ):
                                        # Future planned DCA (between slider position and end of window)
                                        st.markdown(
                                            f"""
                                        <style>
                                            .dca-amount-{day_num} .hidden-amount {{
                                                opacity: 0;
                                                transition: opacity 0.2s ease;
                                            }}
                                            .dca-amount-{day_num} .placeholder {{
                                                opacity: 1;
                                                transition: opacity 0.2s ease;
                                            }}
                                            .dca-amount-{day_num}:hover .hidden-amount {{
                                                opacity: 1;
                                            }}
                                            .dca-amount-{day_num}:hover .placeholder {{
                                                opacity: 0;
                                            }}
                                        </style>
                                        <div style="
                                            border: 2px dashed #9CA3AF;
                                            border-radius: 8px;
                                            padding: 8px;
                                            margin: 2px;
                                            background-color: rgba(156,163,175,0.1);
                                            text-align: center;
                                            min-height: 80px;
                                        ">
                                            <div style="font-weight: bold; color: #fff; font-size: 14px;">
                                                {day_num}
                                            </div>
                                            <div style="font-size: 16px; color: #6B7280; margin: 2px 0;">
                                                ⏳
                                            </div>
                                            <div class="dca-amount-{day_num}" style="
                                                font-size: 16px; 
                                                color: #fff; 
                                                margin: 2px 0;
                                                position: relative;
                                                cursor: pointer;
                                            ">
                                                <strong class="hidden-amount">${future_dca_amount:.2f}</strong>
                                                <span class="placeholder" style="
                                                    position: absolute;
                                                    left: 50%;
                                                    transform: translateX(-50%);
                                                    top: 0;
                                                ">***</span>
                                            </div>
                                            <div style="font-size: 9px; color: #fff; margin: 2px 0;">
                                                Planned DCA
                                            </div>
                                        </div>
                                        """,
                                            unsafe_allow_html=True,
                                        )
                                    elif (
                                        current_date.date()
                                        <= slider_current_date.date()
                                    ):
                                        # Past day (before slider position) with no purchase
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
                                            <div style="font-weight: bold; color: #161B22; font-size: 14px;">
                                                {day_num}
                                            </div>
                                            <div style="font-size: 10px; color: #F7931A; margin: 2px 0;">
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
        legend_cols = st.columns(6)
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
        with legend_cols[5]:
            st.markdown(
                "⏳ **Planned**<br/>Future DCA allocation", unsafe_allow_html=True
            )


def render_accumulation_advantage(dynamic_perf, uniform_perf, df_window):
    """
    Render Accumulation Advantage visualization showing cumulative sats advantage
    """
    import plotly.graph_objects as go

    analyzer = AccumulationAnalyzer(dynamic_perf, uniform_perf, df_window)

    # Get advantage data
    sats_adv = analyzer.sats_advantage()
    progress_data = analyzer.accumulation_progress_over_time()

    # Display big number metrics - Robinhood style
    st.markdown("### 🎯 Your Accumulation Advantage")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Format satoshis with proper sign
        sats_sign = "+" if sats_adv['sats'] >= 0 else ""
        st.markdown(
            f"""
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 15px; color: white;">
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">{"Extra" if sats_adv['sats'] >= 0 else "Fewer"} Satoshis vs DCA</div>
                <div style="font-size: 36px; font-weight: bold; margin: 10px 0;">
                    {sats_sign}{sats_adv['sats']:,}
                </div>
                <div style="font-size: 16px; opacity: 0.9;">sats</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        # Format with proper +/- sign
        sign = "+" if sats_adv['percentage'] >= 0 else ""
        st.markdown(
            f"""
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #f7931a 0%, #f5ab35 100%);
                        border-radius: 15px; color: white;">
                <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">Advantage Over DCA</div>
                <div style="font-size: 36px; font-weight: bold; margin: 10px 0;">
                    {sign}{sats_adv['percentage']:.2f}%
                </div>
                <div style="font-size: 16px; opacity: 0.9;">{"more" if sats_adv['percentage'] >= 0 else "less"} Bitcoin</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        if not progress_data.empty:
            final_dynamic_btc = progress_data["Total_BTC_dynamic"].iloc[-1]
            st.markdown(
                f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                            border-radius: 15px; color: white;">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">Total BTC Accumulated</div>
                    <div style="font-size: 36px; font-weight: bold; margin: 10px 0;">
                        {final_dynamic_btc:.6f}
                    </div>
                    <div style="font-size: 16px; opacity: 0.9;">₿</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Cumulative advantage chart
    if not progress_data.empty:
        st.markdown("#### 📈 Advantage Growth Over Time")
        st.info("This chart shows how much more Bitcoin you're accumulating compared to simple DCA")

        fig = go.Figure()

        # Area chart showing cumulative advantage
        fig.add_trace(
            go.Scatter(
                x=progress_data["Date"],
                y=progress_data["Sats_Advantage"],
                mode="lines",
                name="Sats Advantage",
                line=dict(color="#667eea", width=0),
                fill="tozeroy",
                fillcolor="rgba(102, 126, 234, 0.3)",
                hovertemplate="<b>%{x}</b><br>Advantage: %{y:,.0f} sats<extra></extra>"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=progress_data["Date"],
                y=progress_data["Sats_Advantage"],
                mode="lines",
                name="Advantage Line",
                line=dict(color="#667eea", width=3),
                showlegend=False,
                hovertemplate="<b>%{x}</b><br>Advantage: %{y:,.0f} sats<extra></extra>"
            )
        )

        fig.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Cumulative Sats Advantage",
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(fig, config={"displayModeBar": True}, width="stretch")

        # Simple explanation
        final_advantage_pct = sats_adv['percentage']
        if final_advantage_pct >= 0:
            st.success(
                f"💡 **What this means**: By using the dynamic strategy instead of simple DCA, "
                f"you've accumulated **{final_advantage_pct:.1f}% more Bitcoin** with the same budget. "
                f"That's **{sats_adv['sats']:,} extra satoshis** in your pocket!"
            )
        else:
            st.warning(
                f"📊 **Current Performance**: The dynamic strategy has accumulated **{abs(final_advantage_pct):.1f}% less Bitcoin** "
                f"compared to uniform DCA in this period. This can happen during certain market conditions. "
                f"Consider adjusting strategy parameters or extending the time window for better results."
            )


def render_smart_timing_heatmap(dynamic_perf, uniform_perf, df_window):
    """
    Render Smart Timing Heatmap showing purchase efficiency by day
    """
    import plotly.graph_objects as go
    import calendar

    analyzer = AccumulationAnalyzer(dynamic_perf, uniform_perf, df_window)
    heatmap_data = analyzer.daily_efficiency_heatmap_data()

    if heatmap_data.empty:
        st.info("No data available for timing analysis")
        return

    st.markdown("### 🎯 Smart Timing Heatmap")
    st.info("Darker green = bought at better prices. This shows how well the algorithm times the market.")

    # Group by month for monthly heatmaps
    heatmap_data['YearMonth'] = pd.to_datetime(heatmap_data['Date']).dt.to_period('M')

    for period in sorted(heatmap_data['YearMonth'].unique()):
        month_data = heatmap_data[heatmap_data['YearMonth'] == period].copy()

        if month_data.empty:
            continue

        month_start = pd.to_datetime(month_data['Date'].iloc[0])

        with st.expander(f"📅 {month_start.strftime('%B %Y')}", expanded=True):
            # Create calendar matrix
            year = month_start.year
            month = month_start.month
            cal = calendar.monthcalendar(year, month)

            # Create efficiency matrix
            efficiency_matrix = []
            text_matrix = []

            for week in cal:
                week_efficiency = []
                week_text = []
                for day in week:
                    if day == 0:
                        week_efficiency.append(None)
                        week_text.append("")
                    else:
                        day_date = pd.Timestamp(year=year, month=month, day=day)
                        day_row = month_data[pd.to_datetime(month_data['Date']).dt.date == day_date.date()]

                        if not day_row.empty:
                            efficiency = day_row['Efficiency'].iloc[0]
                            price = day_row['Price'].iloc[0]
                            amount = day_row['Amount_Spent'].iloc[0]
                            week_efficiency.append(efficiency)
                            week_text.append(
                                f"Day {day}<br>Efficiency: {efficiency:.1f}/100<br>"
                                f"Price: ${price:,.0f}<br>Spent: ${amount:.0f}"
                            )
                        else:
                            week_efficiency.append(None)
                            week_text.append(f"Day {day}")

                efficiency_matrix.append(week_efficiency)
                text_matrix.append(week_text)

            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=efficiency_matrix,
                text=text_matrix,
                hovertemplate='%{text}<extra></extra>',
                colorscale=[
                    [0, '#fee5d9'],
                    [0.25, '#fcbba1'],
                    [0.5, '#fc9272'],
                    [0.75, '#a1d99b'],
                    [1, '#31a354']
                ],
                showscale=True,
                colorbar=dict(
                    title=dict(
                        text="Efficiency<br>Score",
                        side="right"
                    ),
                    tickmode="linear",
                    tick0=0,
                    dtick=25
                ),
                zmin=0,
                zmax=100
            ))

            # Update layout
            fig.update_layout(
                xaxis=dict(
                    tickmode='array',
                    tickvals=[0, 1, 2, 3, 4, 5, 6],
                    ticktext=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    side='top'
                ),
                yaxis=dict(
                    showticklabels=False,
                    autorange='reversed'
                ),
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
            )

            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_efficiency_metrics_cards(dynamic_perf, uniform_perf, df_window):
    """
    Render efficiency metrics comparison cards - Robinhood style
    """
    analyzer = AccumulationAnalyzer(dynamic_perf, uniform_perf, df_window)

    metrics = analyzer.get_all_efficiency_metrics()
    dip_metrics = analyzer.dip_capture_analysis()
    timing_score = metrics["Timing Intelligence Score"]

    st.markdown("### 📊 Strategy Performance Metrics")

    # Row 1: Main metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Purchase Efficiency",
            f"{timing_score:.1f}/100",
            help="Overall score measuring timing intelligence"
        )

    with col2:
        st.metric(
            "Dip Capture Rate",
            f"{dip_metrics['capture_rate']:.1f}%",
            help="Percentage of price dips successfully captured with increased buying"
        )

    with col3:
        st.metric(
            "Capital Utilization",
            f"{metrics['Capital Utilization (%)']:.1f}%",
            help="How efficiently your capital was deployed"
        )

    with col4:
        btc_adv = metrics['BTC Advantage (%)']
        btc_sign = "+" if btc_adv >= 0 else ""
        st.metric(
            "BTC Advantage",
            f"{btc_sign}{btc_adv:.2f}%",
            help="Percentage more Bitcoin accumulated vs uniform DCA"
        )

    st.markdown("---")

    # Comparison table
    st.markdown("#### 📋 Dynamic Strategy vs Uniform DCA")

    comparison_data = {
        "Metric": [
            "Timing Intelligence Score",
            "Dips Identified",
            "Dips Successfully Captured",
            "Capture Success Rate",
            "Extra Satoshis Accumulated",
            "BTC Advantage"
        ],
        "Value": [
            f"{timing_score:.1f}/100",
            f"{dip_metrics['dip_days']}",
            f"{dip_metrics['captured_dips']}",
            f"{dip_metrics['capture_rate']:.1f}%",
            f"{'+' if metrics['Sats Advantage'] >= 0 else ''}{metrics['Sats Advantage']:,}",
            f"{'+' if metrics['BTC Advantage (%)'] >= 0 else ''}{metrics['BTC Advantage (%)']:.2f}%"
        ],
        "Interpretation": [
            "🟢 Excellent" if timing_score > 75 else "🟡 Good" if timing_score > 50 else "🟠 Fair",
            f"Market had {dip_metrics['dip_days']} opportunities",
            f"Algorithm caught {dip_metrics['captured_dips']} dips",
            "🟢 Strong" if dip_metrics['capture_rate'] > 70 else "🟡 Good" if dip_metrics['capture_rate'] > 50 else "🟠 Moderate",
            "Compared to uniform DCA",
            "You're outperforming!" if metrics['BTC Advantage (%)'] > 0 else "Consider adjusting"
        ]
    }

    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, hide_index=True, width="stretch")

    # Top purchases
    st.markdown("#### 🏆 Top 5 Most Efficient Purchases")
    top_purchases = analyzer.top_purchases(n=5)

    if not top_purchases.empty:
        top_purchases_display = top_purchases.copy()
        top_purchases_display['Date'] = pd.to_datetime(top_purchases_display['Date']).dt.strftime('%Y-%m-%d')
        top_purchases_display['Price'] = top_purchases_display['Price'].apply(lambda x: f"${x:,.0f}")
        top_purchases_display['BTC_Bought'] = top_purchases_display['BTC_Bought'].apply(lambda x: f"{x:.8f} ₿")
        top_purchases_display['Amount_Spent'] = top_purchases_display['Amount_Spent'].apply(lambda x: f"${x:.0f}")
        top_purchases_display['Efficiency'] = top_purchases_display['Efficiency'].apply(lambda x: f"{x:.1f}/100")

        top_purchases_display = top_purchases_display.rename(columns={
            'BTC_Bought': 'BTC Bought',
            'Amount_Spent': 'Amount Spent',
            'Efficiency': 'Efficiency Score'
        })

        st.dataframe(top_purchases_display, hide_index=True, width="stretch")

        st.success(
            f"🎯 **Great timing!** Your best purchase was on {top_purchases.iloc[0]['Date'].strftime('%Y-%m-%d')} "
            f"with an efficiency score of {top_purchases.iloc[0]['Efficiency']:.1f}/100"
        )

    # Educational expander
    with st.expander("ℹ️ Understanding Accumulation Efficiency"):
        st.markdown("""
        **Timing Intelligence Score (0-100)**: A composite score measuring how well the algorithm times purchases.
        - **90-100**: Exceptional - Algorithm is timing the market extremely well
        - **70-89**: Excellent - Strong market timing with consistent dip captures
        - **50-69**: Good - Above-average timing, outperforming simple DCA
        - **Below 50**: Fair - Consider adjusting strategy parameters

        **Dip Capture Rate**: Percentage of identified price dips where the algorithm increased buying allocation.
        - Higher rate = better at "buying the dip"
        - Algorithm identifies dips using rolling average analysis

        **Purchase Efficiency Score**: How close to the optimal price each purchase was made.
        - 100 = bought at lowest price in the period
        - 0 = bought at highest price in the period

        **Why this matters for institutional Bitcoin accumulation**:
        - Small efficiency gains compound significantly over time
        - Better timing means more BTC per dollar spent
        - Systematic approach preserves DCA discipline while improving execution
        """)


def render_strategy_intelligence_tab(dynamic_perf, uniform_perf, df_window):
    """
    Main function to render the Strategy Intelligence tab
    Combines accumulation advantage, timing heatmap, and efficiency metrics
    """
    st.markdown("## 🧠 Strategy Intelligence Dashboard")
    st.markdown("*Demonstrating superior accumulation efficiency through data-driven timing*")
    st.markdown("---")

    # Section 1: Accumulation Advantage
    render_accumulation_advantage(dynamic_perf, uniform_perf, df_window)

    st.markdown("---")

    # Section 2: Efficiency Metrics
    render_efficiency_metrics_cards(dynamic_perf, uniform_perf, df_window)

    st.markdown("---")

    # Section 3: Smart Timing Heatmap
    render_smart_timing_heatmap(dynamic_perf, uniform_perf, df_window)
