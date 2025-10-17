# ui/charts.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from model.strategy_new import construct_features  # Assumes this file exists
import config


def render_price_signals_chart(df_chart_display, df_current, weights, df_window):
    """
    Renders the Price & Signals chart.
    - df_chart_display: The extended DataFrame for plotting context lines (Price, MA200).
    - df_current: The DataFrame for the active window to plot signals and weights.
    """
    st.markdown("<h3>Bitcoin Price with Buy Signals</h3>", unsafe_allow_html=True)

    # Calculate features (MA200) on the entire display range for a continuous line
    features = construct_features(df_chart_display)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price & MA200", "Daily Weights"),
    )

    # Plotting Price and MA200 lines using the full df_chart_display (Unchanged)
    hist_data = df_chart_display[df_chart_display["Type"] == "Historical"]
    forecast_data = df_chart_display[df_chart_display["Type"] == "Forecast"]

    fig.add_trace(
        go.Scatter(
            x=hist_data.index,
            y=hist_data["PriceUSD"],
            name="Historical Price",
            line=dict(color="#f7931a", width=2.5),
        ),
        row=1,
        col=1,
    )
    if not forecast_data.empty:
        fig.add_trace(
            go.Scatter(
                x=forecast_data.index,
                y=forecast_data["PriceUSD"],
                name="Forecasted Price",
                line=dict(color="#f7931a", width=2.5, dash="dash"),
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=df_chart_display.index,
            y=features["ma200"],
            name="MA200",
            line=dict(color="#667eea", width=2, dash="dash"),
        ),
        row=1,
        col=1,
    )
    fig.add_vline(
        x=pd.to_datetime(config.HISTORICAL_END).timestamp() * 1000,
        line_width=2,
        line_dash="dot",
        line_color="grey",
        annotation_text="Forecast Begins",
        annotation_position="top left",
    )

    fig.add_vline(
        x=pd.to_datetime(df_current.index[0]).timestamp() * 1000,
        line_width=2,
        line_dash="dot",
        line_color="grey",
        annotation_text="Accumulation Start Date",
        annotation_position="top left",
    )

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ START OF UPDATED SECTION: PLOTTING HISTORICAL & ACTIVE SIGNALS   ║
    # ╚══════════════════════════════════════════════════════════════════╝

    # --- 1. Plot Historical Context Signals (fixed size) ---
    # Isolate the part of the chart that comes BEFORE the user's selected window
    window_start_date = df_window.index[0]
    historical_context_df = df_chart_display.loc[
        df_chart_display.index < window_start_date
    ]

    # Find where the buy condition was met in that historical period
    historical_signals = (
        historical_context_df["PriceUSD"]
        < features.loc[historical_context_df.index, "ma200"]
    )

    # Add a trace for these historical signals with a distinct, fixed-size marker
    fig.add_trace(
        go.Scatter(
            x=historical_context_df.index[historical_signals],
            y=historical_context_df.loc[historical_signals, "PriceUSD"],
            mode="markers",
            name="Historical Buy Condition",  # New legend name
            marker=dict(
                size=6,  # Fixed small size
                color="#1CBDE6",  # Different color for distinction
                symbol="diamond",  # Different symbol for clarity
                opacity=0.8,
            ),
            hovertemplate="<b>Signal Condition Met</b><br>Price: $%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # --- 2. Plot Active Window Signals (variable size) ---
    # This shows the actual buys executed by the simulation in the selected window.
    active_signals = df_current["PriceUSD"] < features.loc[df_current.index, "ma200"]

    # We need to handle the case where there are no active signals yet to avoid errors
    if active_signals.any():
        fig.add_trace(
            go.Scatter(
                x=df_current.index[active_signals],
                y=df_current.loc[active_signals, "PriceUSD"],
                mode="markers",
                name="Buy Signal",  # More descriptive name
                marker=dict(
                    size=weights.loc[df_current.index][active_signals]
                    * 2000,  # Variable size
                    color="red",  # Original strong color
                    opacity=0.2,
                    line=dict(width=1, color="darkred"),
                ),
                hovertemplate="<b>Buy Signal</b><br>Price: $%{y:,.2f}<br>Weight: %{customdata:.5f}<extra></extra>",
                customdata=weights.loc[df_current.index][
                    active_signals
                ],  # Add weight to hover text
            ),
            row=1,
            col=1,
        )

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║ END OF UPDATED SECTION                                           ║
    # ╚══════════════════════════════════════════════════════════════════╝

    # Weights plot only for the active window (Unchanged)
    fig.add_trace(
        go.Bar(
            x=df_current.index,
            y=weights.loc[df_current.index],
            name="Daily Weight",
            marker_color="#667eea",
            hovertemplate="Weight: %{y:.6f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=1 / len(df_window),
        line_dash="dash",
        line_color="orange",
        annotation_text="Uniform DCA",
        row=2,
        col=1,
    )

    fig.update_layout(
        height=700,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Price (USD)", type="log", row=1, col=1)
    fig.update_yaxes(title_text="Weight", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)


def render_weight_distribution_chart(weights, df_current):
    """Renders the Weight Distribution content for Tab 2."""
    st.markdown("### Daily Weight Distribution")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Average", f"{weights.mean():.6f}")
    with col2:
        st.metric("Maximum", f"{weights.max():.6f}")
    with col3:
        st.metric("Minimum", f"{weights.min():.6f}")
    with col4:
        st.metric("Std Dev", f"{weights.std():.6f}")

    # This chart was incomplete in the original file, so I'm creating a simple bar chart.
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_current.index,
            y=weights.loc[df_current.index],
            name="Daily Weight",
            marker_color="#667eea",
        )
    )
    fig.update_layout(
        title="Daily Weight Allocation Over Time",
        xaxis_title="Date",
        yaxis_title="Weight",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bayesian_learning_chart():
    """Renders the Bayesian Learning chart for Tab 3."""
    st.markdown("### Bayesian Belief Evolution")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Prior Mean", f"{st.session_state.prior_mean:.6f}")
    with col2:
        st.metric("Prior Variance", f"{st.session_state.prior_var:.6f}")
    with col3:
        confidence = (
            1 / st.session_state.prior_var if st.session_state.prior_var > 0 else 0
        )
        st.metric("Confidence", f"{confidence:.2f}")

    if len(st.session_state.bayesian_history) > 0:
        hist_df = pd.DataFrame(st.session_state.bayesian_history)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=hist_df["day"],
                y=hist_df["confidence"],
                mode="lines+markers",
                name="Confidence Level",
                line=dict(color="#8b5cf6", width=2),
                fill="tozeroy",
            )
        )
        fig.update_layout(
            height=400,
            xaxis_title="Day",
            yaxis_title="Confidence (1/Variance)",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ Bayesian updates will appear after day 7")


def render_strategy_comparison_chart(dynamic_perf, uniform_perf):
    """Renders the Strategy Comparison chart for Tab 4."""
    st.markdown("### Strategy Performance Comparison")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dynamic_perf["Date"],
            y=dynamic_perf["Cumulative_SPD"],
            name="Dynamic Strategy",
            line=dict(color="#667eea", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=uniform_perf["Date"],
            y=uniform_perf["Cumulative_SPD"],
            name="Uniform DCA",
            line=dict(color="#f7931a", width=3, dash="dash"),
        )
    )
    fig.update_layout(
        height=500,
        xaxis_title="Date",
        yaxis_title="Cumulative Sats-per-Dollar",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
