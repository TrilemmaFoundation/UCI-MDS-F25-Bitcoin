# data_loader.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from config import BACKTEST_START, HISTORICAL_END, MAX_FORECAST_DAYS


def get_current_btc_price():
    """
    Fetch the current Bitcoin price from CoinGecko API (free, no API key required).

    Returns:
        float: Current BTC price in USD, or None if fetch fails.
    """
    try:
        # CoinGecko free API - no authentication required
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = float(data["bitcoin"]["usd"])
        print(f"Current BTC Price: ${price:,.2f}")
        return price
    except Exception as e:
        print(f"Warning: Could not fetch current BTC price from CoinGecko: {e}")
        # Fallback: try alternative free API
        try:
            url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["data"]["amount"])
            print(f"Current BTC Price (from Coinbase): ${price:,.2f}")
            return price
        except Exception as e2:
            print(f"Warning: Fallback API also failed: {e2}")
            return None


def generate_future_data(historical_df, forecast_days, current_price=None):
    """
    Generate simulated future price data using Geometric Brownian Motion (GBM).
    Forecast starts from TODAY and goes into the future.

    Args:
        historical_df (pd.DataFrame): DataFrame with historical price data.
        forecast_days (int): Number of days to project into the future.
        current_price (float, optional): Today's actual BTC price. If None, uses last historical price.

    Returns:
        pd.DataFrame: A DataFrame with future dates and simulated prices.
    """
    # Calculate log returns from historical data to find drift and volatility
    log_returns = np.log(historical_df["PriceUSD"] / historical_df["PriceUSD"].shift(1))
    mu = log_returns.mean()  # Drift
    sigma = log_returns.std()  # Volatility

    # Use current price if available, otherwise fall back to last historical price
    if current_price is not None:
        starting_price = current_price
        print(f"Using live current price: ${starting_price:,.2f}")
    else:
        starting_price = historical_df["PriceUSD"].iloc[-1]
        print(f"Using last historical price: ${starting_price:,.2f}")

    # Start forecast from TODAY (current date)
    today = pd.Timestamp.now().normalize()

    print(f"Starting forecast from: {today}")

    # Create a date range for the forecast period starting TODAY
    future_dates = pd.date_range(start=today, periods=forecast_days)

    # Generate random shocks for the GBM model
    Z = np.random.standard_normal(size=forecast_days)
    daily_returns = np.exp(mu - 0.5 * sigma**2 + sigma * Z)

    # Generate the price path starting from today's price
    future_prices = np.zeros(forecast_days)
    future_prices[0] = starting_price * daily_returns[0]
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
    Historical data goes up to HISTORICAL_END.
    Forecast starts from TODAY and goes MAX_FORECAST_DAYS into the future.
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
        print(
            f"Historical data range: {btc_df_hist.index[0]} to {btc_df_hist.index[-1]}"
        )

        # Add a 'Type' column to identify this as real data
        btc_df_hist["Type"] = "Historical"

        # --- Step 2: Fetch Current BTC Price ---
        current_price = get_current_btc_price()

        # --- Step 3: Generate and Append Future Data (starts from TODAY) ---
        btc_df_future = generate_future_data(
            btc_df_hist, MAX_FORECAST_DAYS, current_price
        )

        print(
            f"Forecast data range: {btc_df_future.index[0]} to {btc_df_future.index[-1]}"
        )

        # --- Step 4: Combine and Return ---
        combined_df = pd.concat([btc_df_hist, btc_df_future])
        return combined_df

    except requests.exceptions.RequestException as e:
        st.error(f"Network error loading Bitcoin data: {e}")
        return None
    except Exception as e:
        st.error(f"Error processing Bitcoin data: {e}")
        return None
