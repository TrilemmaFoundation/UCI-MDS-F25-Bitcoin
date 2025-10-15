# ui/header.py
import streamlit as st
import pandas as pd


def render_header(df_btc, yesterday_formatted):
    """Renders the main header and data information box."""
    st.markdown(
        '<p class="main-header">₿ Bitcoin Bayesian Accumulation Dashboard</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Dynamic Buy-The-Dip Strategy with Real-Time Bayesian Learning</p>',
        unsafe_allow_html=True,
    )
    st.toast("✅ Data Loaded Successfully (coinmetrics.com)")
    st.markdown(
        f"""
    <div class="info-box">
    📅 Period: {df_btc.index[0].strftime('%Y-%m-%d')} to today ({yesterday_formatted})<br>
    📊 Total Days: {len(df_btc):,} | 💰 Current Price: ${df_btc.iloc[-1]['PriceUSD']:,.2f})<br><br>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
