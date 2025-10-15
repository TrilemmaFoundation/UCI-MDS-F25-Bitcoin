# ui/validation.py
import streamlit as st
import numpy as np
from config import MIN_WEIGHT


def render_validation(weights, dynamic_perf, budget, current_day):
    """Renders the strategy validation section."""
    st.markdown("### ✅ Strategy Validation")

    weight_sum = weights.sum()
    val_col1, val_col2, val_col3, val_col4 = st.columns(4)

    with val_col1:
        if np.isclose(weight_sum, 1.0, rtol=1e-5):
            st.success(f"✅ Weights Sum: {weight_sum:.6f}")
        else:
            st.warning(f"⚠️ Weights Sum: {weight_sum:.6f}")

    with val_col2:
        if (weights >= MIN_WEIGHT).all():
            st.success(f"✅ Min Weight: {weights.min():.6f}")
        else:
            st.error(f"❌ Min Weight: {weights.min():.6f}")

    with val_col3:
        expected_spend = budget * weights.iloc[: current_day + 1].sum()
        actual_spend = dynamic_perf.iloc[-1]["Total_Spent"]
        if np.isclose(expected_spend, actual_spend, rtol=1e-3):
            st.success(f"✅ Spent: ${actual_spend:,.2f}")
        else:
            st.warning(f"⚠️ Spent: ${actual_spend:,.2f}")

    with val_col4:
        remaining = dynamic_perf.iloc[-1]["Remaining_Budget"]
        st.info(f"💰 Remaining: ${remaining:,.2f}")

    with st.expander("🔍 Budget Allocation Details"):
        st.markdown(
            f"""
        **Budget Mechanics:**
        The weights represent a **pre-planned allocation** across the entire 12-month period:
        - **Total Budget:** ${budget:,.2f}
        - **Weight Sum (Full Window):** {weights.sum():.6f} (should be ~1.0)
        - **Weights Used So Far:** {weights.iloc[:current_day+1].sum():.6f}
        - **Expected Spend to Date:** ${budget * weights.iloc[:current_day+1].sum():,.2f}
        - **Actual Spend to Date:** ${actual_spend:,.2f}
        - **Remaining Weights:** {weights.iloc[current_day+1:].sum():.6f}
        - **Remaining Budget:** ${remaining:,.2f}
        
        **Key Insight:** Each day's allocation (weight × total_budget) is independent and pre-determined.
        This is NOT a "remaining budget" model where you split what's left. Instead, it's a strategic
        allocation plan where you commit specific amounts to each day based on expected market conditions.
        """
        )

    if not np.isclose(weight_sum, 1.0, rtol=1e-5):
        st.warning(
            "⚠️ **Weight sum deviation detected.** This may indicate an issue with the strategy calculation."
        )

    st.markdown("---")
