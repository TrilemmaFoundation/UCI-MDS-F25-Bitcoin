# ui/recommendations.py
import streamlit as st
import pandas as pd
from dashboard.model.strategy_new import construct_features, get_buy_signal_strength


def render_recommendations(dynamic_perf, df_current, weights, budget, current_day):
    """
    Renders the 'Action Plan' section for the currently selected day.
    """
    # Get data for the specific day being simulated
    sim_slice = df_current.iloc[: current_day + 1]

    if sim_slice.empty:
        st.info("Simulation has not started yet.")
        return

    today_data = sim_slice.iloc[-1]
    today_date = today_data.name.strftime("%Y-%m-%d")  # Get date from index
    today_price = today_data["PriceUSD"]
    today_weight = weights.loc[today_data.name]
    amount_to_invest = budget * today_weight

    st.markdown(f"### Action Plan for {today_date}")
    st.metric("Recommended Investment", f"${amount_to_invest:,.2f}")

    with st.expander("Analysis and Details"):
        # --- Signal Analysis ---
        features = construct_features(sim_slice)
        today_features = features.iloc[-1]
        today_ma200 = today_features["ma200"]
        today_std200 = today_features["std200"]

        z_score = 0
        if (
            pd.notna(today_ma200)
            and pd.notna(today_std200)
            and today_std200 > 0
            and today_price < today_ma200
        ):
            z_score = (today_ma200 - today_price) / today_std200

        signal_strength = get_buy_signal_strength(z_score)

        if signal_strength == "Very Strong" or signal_strength == "Strong":
            st.success(
                f"🟢 {signal_strength.upper()} BUY SIGNAL: Price is significantly below long-term trend. Excellent accumulation opportunity!"
            )
        elif signal_strength == "Moderate":
            st.info(
                f"🔵 {signal_strength.upper()} BUY SIGNAL: Price is below trend. Good time to accumulate more."
            )
        elif signal_strength == "Weak":
            st.warning(
                f"🟡 {signal_strength.upper()} BUY SIGNAL: Slightly favorable conditions. Standard+ allocation."
            )
        else:
            st.markdown(
                "ℹ️ **NEUTRAL / REDUCED ALLOCATION**: Price is at or above the long-term trend. The strategy is conserving capital for better opportunities."
            )

        # --- Data Columns ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
            **Allocation Details:**
            - **Weight:** `{today_weight:.4%}`
            - **Amount to Invest:** `${amount_to_invest:,.2f}`
            - **Expected BTC:** `{(amount_to_invest / today_price):.8f} ₿`
            """
            )
        with col2:
            st.markdown(
                f"""
            **Technical Context:**
            - **Price:** `${today_price:,.2f}`
            - **200-Day MA:** `${today_ma200:,.2f}`
            - **Deviation:** `{((today_price/today_ma200 - 1)*100):.2f}%`
            - **Z-Score:** `{z_score:.2f}`
            """
            )

        # --- Budget Progress ---
        remaining_budget = dynamic_perf.iloc[-1]["Remaining_Budget"]
        spent_pct = (budget - remaining_budget) / budget
        st.metric(
            "Remaining Budget After Today's Purchase", f"${remaining_budget:,.2f}"
        )
        st.progress(spent_pct, text=f"{spent_pct:.1%} of total budget deployed")
