# ui/performance_tabs.py
import streamlit as st
import pandas as pd
from ui.charts import (
    render_price_signals_chart,
    render_weight_distribution_chart,
    render_bayesian_learning_chart,
    render_strategy_comparison_chart,
)


def render_performance(
    df_window, weights, dynamic_perf, uniform_perf, current_day, df_for_chart
):
    """
    Renders key metrics and the main tab layout for visualizations.
    Accepts an additional df_for_chart for historical context.
    """

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

    metrics_data = {
        "Metric": [
            "'Current' BTC Price",
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
    tab1, tab2, tab3 = st.tabs(
        [
            "📈 Price & Signals",
            "⚖️ Weight Distribution",
            # "🧠 Bayesian Learning",
            "📊 Strategy Comparison",
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
    st.markdown("<h3>📊 Performance Metrics</h3>", unsafe_allow_html=True)

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
