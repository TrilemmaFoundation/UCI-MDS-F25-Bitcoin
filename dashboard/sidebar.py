import streamlit as st

# from dashboard.backend.gsheet_utils import get_user_info_by_email
from dashboard.backend.supabase_utils import get_user_info_by_email

from dashboard.ui.update_modal import modal


def render_sidebar():
    """
    Render sidebar with user inputs and configuration options.

    Returns:
        Dictionary containing all user-selected parameters
    """

    # if the user is logged in, retrieve their budget info
    logged_in = False
    st.session_state.user_info = {}
    if st.user.get("email"):
        logged_in = True
        user_info = get_user_info_by_email(st.user.get("email"))
        st.session_state.user_info = user_info if user_info else {}

    with st.sidebar:
        # Logo and branding

        # st.title("⚙️ Configuration")
        # st.markdown("---")

        # Investment Parameters
        st.markdown("### Investment Parameters")
        if st.user.get("email"):
            modal(st.user.get("email"))

        # Set default values
        default_budg_val = 1000
        default_invest_window = 12
        default_boost_val = 1.25

        # Override with user values if logged in and user_info exists
        if logged_in and user_info:
            try:
                default_budg_val = int(user_info.get("budget", 1000))
                default_invest_window = int(user_info.get("investment_period", 12))
                default_boost_val = float(user_info.get("boost_factor", 1.25))
            except (ValueError, TypeError, KeyError):
                # If any conversion fails, keep defaults
                pass

        budget = st.number_input(
            "Total Budget (USD)",
            min_value=100,
            max_value=10_000_000,
            value=default_budg_val,
            step=100,
            help="Total amount you want to invest over the accumulation period",
        )

        investment_window = st.number_input(
            "Investment window (months)",
            min_value=1,
            max_value=24,
            value=default_invest_window,
            step=1,
            help="Amount of months for your investment period",
        )

        # Show derived metrics (Now dynamic)
        if investment_window > 0:
            days_in_period = investment_window * 30.44  # Average days/month
            daily_avg = budget / days_in_period
            monthly_avg = budget / investment_window
        else:
            daily_avg = monthly_avg = 0

        st.markdown(
            f"""
        **Breakdown:**
        - Approx. Daily (DCA): ${daily_avg:,.2f}
        - Monthly: ${monthly_avg:,.2f}
        """
        )
        st.markdown("---")

        # Model Selection
        st.markdown("### Model Selection")
        model_choice = st.selectbox(
            "Choose Strategy Model",
            options=["Base Model", "GT-MSA-S25-Trilemma Model"],
            index=1,
            help="Select which Bitcoin accumulation model to use",
        )

        st.markdown("---")

        # Strategy Parameters (code unchanged)
        st.markdown("### Strategy Parameters")

        # Only show boost_alpha for current model
        if model_choice == "Base Model":
            boost_alpha = st.slider(
                "Boost Factor (α)",
                0.5,
                5.0,
                default_boost_val,
                0.05,
                help="Controls how aggressively to buy during dips.",
            )
            st.info(
                "ℹ️ Choose your boost factor for the base model (71.6% final score with α=1.25)"
            )
        else:
            # For GT model, set a default (model doesn't use this parameter)
            boost_alpha = 1.25
            st.info(
                "ℹ️ GT-MSA-S25-Trilemma model uses optimized parameters (94.5% final score)"
            )

        # Show boost factor interpretation only for current model
        if model_choice == "Base Model":
            if boost_alpha < 1.0:
                boost_desc = "Conservative - Minimal deviation from DCA"
            elif boost_alpha < 1.5:
                boost_desc = "Moderate - Balanced approach"
            elif boost_alpha < 2.0:
                boost_desc = "Aggressive - Strong dip buying"
            else:
                boost_desc = "Very Aggressive - Maximum dip concentration"

            st.caption(f"*{boost_desc}*")

        st.markdown("---")

        # ════════════════════════════════════════════════════════
        # Information Section
        # ════════════════════════════════════════════════════════
        with st.expander("ℹ️ About This Strategy"):
            if model_choice == "Base Model":
                st.markdown(
                    """
                **Dynamic Buy-The-Dip Approach**
                
                This strategy intelligently adjusts daily Bitcoin accumulation based on:
                
                🎯 **Key Features:**
                - 📉 Detects when price drops below 200-day MA
                - 📊 Measures dip significance using Z-scores
                - 💰 Allocates more capital during larger dips
                - ⚖️ Redistributes from future periods
                - 🎲 Updates beliefs using Bayesian inference
                """
                )
            else:
                st.markdown(
                    """
                **GT-MSA-S25-Trilemma Model (94.5% Final Score)**
                
                This sophisticated two-layer system achieved exceptional performance:
                
                🎯 **Key Features:**
                - 🧠 Strategic Layer: Annual investment planning using 5 momentum signals
                - ⚡ Tactical Layer: Daily adjustments based on market conditions
                - 📈 99.4% win rate against uniform DCA since 2011
                - 🔄 Multi-scale cyclical awareness (30d to 4-year signals)
                - 🎯 23 optimized parameters from rigorous backtesting
                
                **Performance Metrics:**
                - Final Score: 94.5%
                - Win Rate: 99.4%
                - Reward-Weighted Percentile: 89.55%
                - Tested on 4,750+ rolling 365-day windows
                """
                )

        # Expandable sections for detailed info
        with st.expander("📚 Technical Indicators"):
            st.markdown(
                """
            **MA200 (Moving Average):**
            - 200-day average price
            - Represents long-term trend
            - Buy signal when price < MA200
            
            **Standard Deviation:**
            - Measures price volatility
            - Higher = more volatile market
            - Used to calculate Z-scores
            
            **Z-Score:**
            - Statistical measure of price deviation
            - Formula: (MA200 - Price) / StdDev
            - Higher = stronger buy signal
            
            **Weight:**
            - Percentage of budget for each day
            - All weights sum to 1.0 (100%)
            - Dynamic: higher on dip days
            """
            )

        with st.expander("💡 Signal Interpretation"):
            st.markdown(
                """
            **Z-Score Ranges:**
            - `0.0-0.5`: Weak signal
            - `0.5-1.0`: Moderate signal
            - `1.0-1.5`: Strong signal
            - `1.5-2.0`: Very strong signal
            - `2.0+`: Extreme opportunity
            
            **Weight Boosting:**
            - Base weight × (1 + α × Z-score)
            - Higher α = more aggressive
            - Excess redistributed to future days
            
            **Example:**
            - Z-score = 2.0, α = 1.25
            - Boost = 1 + (1.25 × 2.0) = 3.5×
            - Weight increases by 250%
            """
            )

        # with st.expander("🧠 Bayesian Learning"):
        #     st.markdown(
        #         """
        #     The model continuously learns from new data:

        #     **How it works:**
        #     1. Starts with neutral prior beliefs
        #     2. Observes recent price movements
        #     3. Updates beliefs using Bayes' theorem
        #     4. Confidence increases over time

        #     **Key Metrics:**
        #     - **Prior Mean**: Expected return
        #     - **Prior Variance**: Uncertainty
        #     - **Confidence**: 1/Variance

        #     As more data arrives, variance decreases
        #     and confidence increases, leading to more
        #     refined predictions.
        #     """
        #     )

        with st.expander("⚠️ Risk Considerations"):
            st.markdown(
                """
            **Important Reminders:**
            
            ⚠️ This is an educational tool
            ⚠️ Past performance ≠ future results
            ⚠️ Cryptocurrency is highly volatile
            ⚠️ Only invest what you can afford to lose
            ⚠️ Not financial advice
            
            **Best Practices:**
            - Start with small amounts to test
            - Understand the strategy logic
            - Monitor performance regularly
            - Adjust parameters based on your risk tolerance
            - Diversify your investments
            """
            )

        st.markdown("---")

        # ════════════════════════════════════════════════════════
        # Quick Reference Section
        # ════════════════════════════════════════════════════════
        with st.expander("🔍 Quick Reference"):
            st.markdown(
                """
            **Framework Constants:**
            - Investment Window: 12 months
            - Purchase Frequency: Daily
            - Min Weight: 0.00001
            - Backtest Period: 2011-2025
            
            **Performance Metrics:**
            - **SPD**: Sats-per-dollar (efficiency)
            - **P&L**: Profit and Loss (returns)
            - **ROI**: Return on Investment (%)
            - **BTC**: Total Bitcoin accumulated
            
            **Comparison Baseline:**
            Uniform DCA = investing equal amounts daily
            (1/365 of budget per day)
            """
            )

        st.markdown("---")

        # Footer
        st.caption("Data sources: CoinMetrics, Coinbase")
        st.caption("Version 1.0 • Updated 2025")

    # Return all parameters as dictionary
    return {
        "budget": budget,
        "boost_alpha": boost_alpha,
        "daily_avg": daily_avg,
        "monthly_avg": monthly_avg,
        "investment_window": investment_window,
        "model_choice": model_choice,
    }
