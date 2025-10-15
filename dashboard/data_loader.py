# data_loader.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from config import BACKTEST_START, HISTORICAL_END, MAX_FORECAST_DAYS


def generate_future_data(historical_df, forecast_days):
    """
    Generate simulated future price data using Geometric Brownian Motion (GBM).

    Args:
        historical_df (pd.DataFrame): DataFrame with historical price data.
        forecast_days (int): Number of days to project into the future.

    Returns:
        pd.DataFrame: A DataFrame with future dates and simulated prices.
    """
    # Calculate log returns from historical data to find drift and volatility
    log_returns = np.log(historical_df["PriceUSD"] / historical_df["PriceUSD"].shift(1))
    mu = log_returns.mean()  # Drift
    sigma = log_returns.std()  # Volatility

    # Get the last known price and date
    last_price = historical_df["PriceUSD"].iloc[-1]
    last_date = historical_df.index[-1]

    # Create a date range for the forecast period
    future_dates = pd.to_datetime(
        pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days)
    )

    # Generate random shocks for the GBM model
    Z = np.random.standard_normal(size=forecast_days)
    daily_returns = np.exp(mu - 0.5 * sigma**2 + sigma * Z)

    # Generate the price path
    future_prices = np.zeros(forecast_days)
    future_prices[0] = last_price * daily_returns[0]
    for t in range(1, forecast_days):
        future_prices[t] = future_prices[t - 1] * daily_returns[t]

    # Create the forecast DataFrame
    forecast_df = pd.DataFrame({"PriceUSD": future_prices}, index=future_dates)
    forecast_df.index.name = "time"

    # Add a 'Type' column to distinguish from real data
    forecast_df["Type"] = "Forecast"

    return forecast_df


@st.cache_data(ttl=3600, show_spinner=False)
def load_bitcoin_data():
    """
    Load historical Bitcoin data and append a future forecast.
    Returns a combined DataFrame with a 'Type' column ('Historical' or 'Forecast').
    """
    try:
        # --- Step 1: Load Historical Data ---
        url = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        btc_df_hist = pd.read_csv(StringIO(response.text))

        # Clean and prepare historical data
        btc_df_hist["time"] = pd.to_datetime(btc_df_hist["time"]).dt.normalize()
        btc_df_hist = btc_df_hist.set_index("time").tz_localize(None)
        btc_df_hist = btc_df_hist.loc[
            ~btc_df_hist.index.duplicated(keep="last")
        ].sort_index()

        if "PriceUSD" not in btc_df_hist.columns:
            st.error("Data missing 'PriceUSD' column")
            return None

        btc_df_hist = btc_df_hist.loc[BACKTEST_START:HISTORICAL_END]

        # Add a 'Type' column to identify this as real data
        btc_df_hist["Type"] = "Historical"

        # --- Step 2: Generate and Append Future Data ---
        btc_df_future = generate_future_data(btc_df_hist, MAX_FORECAST_DAYS)

        # --- Step 3: Combine and Return ---
        combined_df = pd.concat([btc_df_hist, btc_df_future])

        return combined_df

    except requests.exceptions.RequestException as e:
        st.error(f"Network error loading Bitcoin data: {e}")
        return None
    except Exception as e:
        st.error(f"Error processing Bitcoin data: {e}")
        return None
