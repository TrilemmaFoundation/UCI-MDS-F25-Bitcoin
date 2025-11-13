# ui/charts.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.model.strategy_new import construct_features
import dashboard.config as config
from datetime import datetime
from dashboard.config import get_today


def render_price_signals_chart(df_chart_display, weights, df_window, current_day):
    """
    Renders the Price & Signals chart.
    - current_day: The current day index (0-based) to slice data up to.
    """
    st.markdown("<h3>Bitcoin Price with Buy Signals</h3>", unsafe_allow_html=True)

    # Slice the window data up to the current day (inclusive, using 0-based index)
    df_current_slice = df_window.iloc[: current_day + 1]

    # Calculate features on the entire display range for continuous MA200 line
    features = construct_features(df_chart_display)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price & MA200", "Daily Weights"),
    )

    # --- Plot main price and MA200 lines ---
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
            x=features.index,
            y=features["ma200"],
            name="MA200",
            line=dict(color="#667eea", width=2, dash="dash"),
        ),
        row=1,
        col=1,
    )

    fig.add_vline(
        x=get_today(),
        line_width=2,
        line_dash="dot",
        line_color="grey",
    )

    fig.add_annotation(
        x=get_today(),
        y=0.4,  # 1 = top of plotting area when yref='paper'
        xref="x",
        yref="paper",
        text=f"Today ({get_today().date()})",
        showarrow=False,
        xanchor="left",  # similar to "top left" placement
        yanchor="auto",
        bgcolor="rgba(255,255,255,0.05)",  # optional styling
        bordercolor="rgba(0,0,0,0.0)",
        font=dict(size=11),
    )

    # --- Add Reference V-Lines ---

    fig.add_vline(
        x=df_window.index[0],
        line_width=2,
        line_dash="dot",
        line_color="grey",
    )

    fig.add_annotation(
        x=df_window.index[0],
        y=0.4,  # 1 = top of plotting area when yref='paper'
        xref="x",
        yref="paper",
        text=f"Accumulation Start",
        showarrow=False,
        xanchor="right",  # similar to "top left" placement
        yanchor="auto",
        bgcolor="rgba(255,255,255,0.05)",  # optional styling
        bordercolor="rgba(0,0,0,0.0)",
        font=dict(size=11),
    )

    # --- Plot Buy Signals ---
    # Find all potential buy signals in the active window slice
    features_slice = features.loc[df_current_slice.index]
    buy_condition = features_slice["PriceUSD"] < features_slice["ma200"]

    if buy_condition.any():
        signal_dates = features_slice.index[buy_condition]
        signal_prices = features_slice.loc[buy_condition, "PriceUSD"]
        signal_weights = weights.loc[signal_dates]

        # Use weights to determine marker size for visual emphasis
        min_w, max_w = weights.min(), weights.max()
        normalized_size = 15 + ((signal_weights - min_w) / (max_w - min_w + 1e-9)) * 25

        fig.add_trace(
            go.Scatter(
                x=signal_dates,
                y=signal_prices,
                mode="markers",
                name="Buy Signal",
                marker=dict(
                    size=normalized_size,
                    color="red",
                    opacity=0.4,
                    line=dict(width=1, color="darkred"),
                ),
                hovertemplate="<b>Buy Signal</b><br>Price: $%{y:,.2f}<br>Weight: %{customdata:.5f}<extra></extra>",
                customdata=signal_weights,
            ),
            row=1,
            col=1,
        )

    # --- Plot Weights Bar Chart ---
    weights_slice = weights.loc[df_current_slice.index]
    fig.add_trace(
        go.Bar(
            x=weights_slice.index,
            y=weights_slice,
            name="Daily Weight",
            marker_color="#667eea",
            hovertemplate="Weight: %{y:.6f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Add reference line for uniform DCA
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
    st.plotly_chart(fig, config={"displayModeBar": True})


# The other chart functions are okay and are omitted for brevity.
# ... (render_weight_distribution_chart, etc. remain here) ...
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

    # Weight distribution bar chart
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
    st.plotly_chart(fig, config={"displayModeBar": True})


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
        st.plotly_chart(fig, config={"displayModeBar": True})
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
    st.plotly_chart(fig, config={"displayModeBar": True})
