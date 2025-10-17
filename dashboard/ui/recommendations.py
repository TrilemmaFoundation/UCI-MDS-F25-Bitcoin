# ui/recommendations.py
import streamlit as st
import pandas as pd
from model.strategy_new import construct_features  # Assumes this file exists


def render_recommendations(
    dynamic_perf, df_current, weights, budget, current_day, current_date
):
    """Renders the 'Today's Action Plan' section."""

    if current_day < len(dynamic_perf):
        today_data = dynamic_perf.iloc[-1]
        today = str(current_date - pd.DateOffset(days=1))[:10]
        st.markdown(
            f"### {today} Action Plan: Invest ${today_data['Amount_Spent']:.2f}"
        )
        today_weight = today_data["Weight"]
        with st.expander("Daily plan details and analysis"):
            # Determine recommendation type
            avg_weight = weights.mean()
            if today_weight > avg_weight * 2:
                st.markdown(
                    '<div class="success-box"><h4>🟢 STRONG BUY SIGNAL</h4><p>Price is significantly below long-term trend. Excellent accumulation opportunity!</p></div>',
                    unsafe_allow_html=True,
                )
            elif today_weight > avg_weight * 1.5:
                st.markdown(
                    '<div class="info-box"><h4>🔵 MODERATE BUY SIGNAL</h4><p>Price is below trend. Good time to accumulate more.</p></div>',
                    unsafe_allow_html=True,
                )
            elif today_weight > avg_weight:
                st.markdown(
                    '<div class="warning-box"><h4>🟡 LIGHT BUY SIGNAL</h4><p>Slightly favorable conditions. Standard+ allocation.</p></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info(
                    "ℹ️ **REDUCED ALLOCATION** - Price at or above trend. Reduced position size."
                )

            # Get features for signal analysis
            features = construct_features(df_current)
            today_ma200 = features.iloc[-1]["ma200"]
            today_std200 = features.iloc[-1]["std200"]
            z_score = 0
            if (
                pd.notna(today_ma200)
                and pd.notna(today_std200)
                and today_std200 > 0
                and today_data["Price"] < today_ma200
            ):
                z_score = (today_ma200 - today_data["Price"]) / today_std200

            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(
                    f"""
                **Allocation Details:**
                - **Amount to Invest:** ${today_data["Amount_Spent"]:.2f}
                - **Weight:** {today_weight:.6f} ({today_weight*100:.3f}% of budget)
                - **Expected BTC:** {today_data["BTC_Bought"]:.8f} ₿
                
                **Technical Analysis:**
                - **BTC Price {today}** ${today_data["Price"]:,.2f}
                - **MA200:** ${today_ma200:,.2f}
                - **Price vs MA200:** {((today_data["Price"]/today_ma200 - 1)*100):+.2f}%
                - **Z-Score:** {z_score:.2f}
                """
                )

            with col2:
                remaining = today_data["Remaining_Budget"]
                spent_pct = (budget - remaining) / budget
                st.metric("Remaining Budget", f"${remaining:,.2f}")
                st.progress(spent_pct, text=f"{spent_pct*100:.1f}% deployed")
