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


def render_performance(
    df_window,
    weights,
    dynamic_perf,
    uniform_perf,
    current_day,
    df_for_chart,
    model_choice=None,
):
    """
    Renders key metrics and the main tab layout for visualizations.
    Accepts an additional df_for_chart for historical context.
    """

    # Display model information
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
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📈 Price & Signals",
            "⚖️ Weight Distribution",
            "📊 Strategy Comparison",
            "📅 Purchasing Schedule",
        ]
    )

    df_current = df_window.iloc[: current_day + 1]

    with tab1:
        # Pass both the extended chart data and the actual current window data
        render_price_signals_chart(
            df_chart_display=df_for_chart,
            df_current=df_current,
            weights=weights,
            df_window=df_window,
        )
    with tab2:
        render_weight_distribution_chart(weights, df_current)
    # with tab3:
    #     render_bayesian_learning_chart()
    with tab3:
        render_strategy_comparison_chart(dynamic_perf, uniform_perf)
        render_comparison_summary(
            dynamic_btc,
            uniform_btc,
            dynamic_perf,
            uniform_perf,
            dynamic_spd,
            uniform_spd,
            btc_advantage,
            spd_advantage,
            dynamic_perf.iloc[-1]["PnL"],
        )
    with tab4:
        render_purchasing_calendar(df_current, dynamic_perf, weights, current_day)
    st.markdown("<h3>Performance Metrics</h3>", unsafe_allow_html=True)

    st.dataframe(pd.DataFrame(metrics_data), hide_index=True)
    st.markdown("---")


def render_comparison_summary(
    dynamic_btc,
    uniform_btc,
    dynamic_perf,
    uniform_perf,
    dynamic_spd,
    uniform_spd,
    btc_advantage,
    spd_advantage,
    dynamic_pnl,
):
    """Renders the summary tables and advantage metrics for the comparison tab."""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Dynamic Strategy")
        st.markdown(
            f"- **Total BTC:** {dynamic_btc:.8f} ₿\n- **Avg Entry:** ${dynamic_perf.iloc[-1]['Avg_Entry_Price']:,.2f}\n- **Total SPD:** {dynamic_spd:,.0f}\n- **P&L:** ${dynamic_perf.iloc[-1]['PnL']:,.2f} ({dynamic_perf.iloc[-1]['PnL_Pct']:+.2f}%)"
        )
    with col2:
        st.markdown("#### Uniform DCA")
        st.markdown(
            f"- **Total BTC:** {uniform_btc:.8f} ₿\n- **Avg Entry:** ${uniform_perf.iloc[-1]['Avg_Entry_Price']:,.2f}\n- **Total SPD:** {uniform_spd:,.0f}\n- **P&L:** ${uniform_perf.iloc[-1]['PnL']:,.2f} ({uniform_perf.iloc[-1]['PnL_Pct']:+.2f}%)"
        )

    st.markdown("---")
    st.markdown("### 🎯 Strategy Advantage")
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        st.metric(
            "Additional BTC",
            f"{dynamic_btc - uniform_btc:+.8f} ₿",
            f"{btc_advantage:+.2f}%",
        )
    with adv_col2:
        st.metric(
            "SPD Advantage",
            f"{dynamic_spd - uniform_spd:+,.0f}",
            f"{spd_advantage:+.2f}%",
        )
    with adv_col3:
        pnl_diff = dynamic_pnl - uniform_perf.iloc[-1]["PnL"]
        st.metric("P&L Advantage", f"${pnl_diff:+,.2f}")


def render_purchasing_calendar(df_current, dynamic_perf, weights, current_day):
    """
    Render a calendar-style view of the purchasing schedule showing past days and current day only.
    Shows BTC price, buy indicators, and amount purchased for each day.
    """
    # Only show past days and current day (no future days)
    current_data = dynamic_perf.iloc[: current_day + 1].copy()

    if current_data.empty:
        st.info("No purchasing data available for the selected time period.")
        return

    # Get features for price analysis
    try:
        features = construct_features(df_current)
    except Exception as e:
        st.error(f"Error constructing features: {e}")
        return

    st.markdown("### 📅 Daily Purchasing Schedule")
    st.markdown("*Invest $ Daily plan details and analysis*")

    # Calculate average weight for signal determination
    avg_weight = weights.mean() if len(weights) > 0 else 0

    # Get the date range for the calendar
    start_date = current_data.iloc[0]["Date"]
    end_date = current_data.iloc[-1]["Date"]

    # Create calendar view
    calendar_container = st.container()

    with calendar_container:
        # Group data by month and year for better organization
        current_data["YearMonth"] = current_data["Date"].dt.to_period("M")

        for period in sorted(current_data["YearMonth"].unique()):
            month_data = current_data[current_data["YearMonth"] == period]
            month_start = month_data.iloc[0]["Date"]

            # Display month header
            st.markdown(f"### {month_start.strftime('%B %Y')}")

            # Create calendar grid for the month
            month_year = period.to_timestamp()
            first_day = month_year.replace(day=1)

            # Get the number of days in the month and the starting weekday
            days_in_month = cal_module.monthrange(first_day.year, first_day.month)[1]
            first_weekday = first_day.weekday()  # Monday = 0, Sunday = 6

            # Create month view with day cells
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            # Day headers
            header_cols = st.columns(7)
            for i, day_name in enumerate(day_names):
                with header_cols[i]:
                    st.markdown(f"**{day_name}**")

            # Create calendar grid - we'll build it week by week
            total_cells = (
                first_weekday + days_in_month
            )  # Total cells needed (empty + days)
            num_weeks = (total_cells + 6) // 7  # Number of weeks to display

            for week in range(num_weeks):
                cols = st.columns(7)
                for day_of_week in range(7):
                    cell_num = week * 7 + day_of_week

                    with cols[day_of_week]:
                        if cell_num < first_weekday:
                            # Empty cell before month starts
                            st.markdown("")
                        elif cell_num < first_weekday + days_in_month:
                            # Day within the month
                            day_num = cell_num - first_weekday + 1
                            current_date = first_day.replace(day=day_num)

                            # Check if this date has purchasing data
                            day_data = month_data[
                                month_data["Date"].dt.date == current_date.date()
                            ]

                            if not day_data.empty:
                                # Get the latest data for this day (in case of duplicates)
                                day_info = day_data.iloc[-1]

                                # Get price analysis
                                price = day_info["Price"]
                                amount_spent = day_info["Amount_Spent"]
                                weight = day_info["Weight"]

                                # Determine buy signal color and indicator
                                signal_color = "gray"
                                signal_emoji = "⚪"
                                signal_text = "Normal"

                                if weight > avg_weight * 2:
                                    signal_color = "green"
                                    signal_emoji = "🟢"
                                    signal_text = "Strong Buy"
                                elif weight > avg_weight * 1.5:
                                    signal_color = "#FFA500"  # Orange
                                    signal_emoji = "🟠"
                                    signal_text = "Moderate Buy"
                                elif weight > avg_weight:
                                    signal_color = "#FFD700"  # Light orange/yellow
                                    signal_emoji = "🟡"
                                    signal_text = "Light Buy"
                                else:
                                    signal_color = "red"
                                    signal_emoji = "🔴"
                                    signal_text = "Reduced"

                                # Create day cell with styling
                                day_style = f"""
                                <div style="
                                    border: 2px solid {signal_color};
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
                                    <div style="font-size: 10px; color: {signal_color}; margin: 2px 0;">
                                        {signal_emoji} {signal_text}
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
                                # No data for this day - only show if it's past or current day
                                if current_date.date() <= datetime.now().date():
                                    # Past day with no data (weekend or holiday)
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
                                    # Future day - don't show
                                    st.markdown("")
                        else:
                            # Empty cell after month ends
                            st.markdown("")

            st.markdown("---")  # Separator between months

        # Add legend
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
