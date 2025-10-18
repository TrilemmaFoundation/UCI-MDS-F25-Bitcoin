# data_loader.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from dashboard.config import BACKTEST_START, HISTORICAL_END, MAX_FORECAST_DAYS


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
    Generate simulated future price data using a modified Geometric Brownian Motion (GBM)
    with realistic constraints for Bitcoin price projections.
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
    historical_mu = log_returns.mean()
    historical_sigma = log_returns.std()

    # Apply modifications for more realistic future projections
    # 1. Add slight positive bias to drift
    mu = historical_mu * 0.3  # Significantly reduce drift

    # 2. Dramatically reduce volatility for constrained range
    sigma = historical_sigma * 0.15  # Only 15% of historical volatility

    # 3. Set maximum daily change limits to prevent large swings
    max_daily_drop = 0.03  # Maximum 3% daily drop
    max_daily_gain = 0.03  # Maximum 3% daily gain

    # 4. Set price bounds
    price_floor = 80000  # Minimum price
    price_ceiling = 150000  # Maximum price

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

    # Generate the price path with momentum and mean reversion
    future_prices = np.zeros(forecast_days)
    future_prices[0] = starting_price

    momentum = 0  # Track short-term momentum
    momentum_decay = 0.85  # How quickly momentum fades

    for t in range(1, forecast_days):
        # Generate random shock
        Z = np.random.standard_normal()

        # Calculate daily return with momentum component
        base_return = mu - 0.5 * sigma**2 + sigma * Z
        daily_return = base_return + momentum * 0.3

        # Apply bounds to prevent extreme moves
        daily_return = np.clip(
            daily_return, np.log(1 - max_daily_drop), np.log(1 + max_daily_gain)
        )

        # Update price
        future_prices[t] = future_prices[t - 1] * np.exp(daily_return)

        # Apply hard price bounds
        future_prices[t] = np.clip(future_prices[t], price_floor, price_ceiling)

        # Update momentum (with decay)
        momentum = momentum * momentum_decay + daily_return * 0.2

        # Remove occasional positive trend reinforcement
        # (Keeping range tight)

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
