# data_loader.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from dashboard.config import BACKTEST_START, TODAY, MAX_FORECAST_DAYS


def get_current_btc_price():
    """
    Fetch the current Bitcoin price from a reliable API.
    Returns:
        float: Current BTC price in USD, or None if fetch fails.
    """
    try:
        url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = float(data["data"]["amount"])
        print(f"Current BTC Price (from Coinbase): ${price:,.2f}")
        return price
    except Exception as e:
        print(f"Warning: Coinbase API failed: {e}. Falling back to CoinGecko.")
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["bitcoin"]["usd"])
            print(f"Current BTC Price (from CoinGecko): ${price:,.2f}")
            return price
        except Exception as e2:
            print(f"CRITICAL: All price APIs failed: {e2}")
            return None


# def generate_future_data(start_price, start_date, forecast_days, historical_df):
#     """
#     Generate simulated future price data using Geometric Brownian Motion (GBM).
#     Forecast starts from the day AFTER today.

#     Args:
#         start_price (float): The starting price for the forecast (today's price).
#         start_date (pd.Timestamp): The date to start the forecast from (tomorrow).
#         forecast_days (int): Number of days to project.
#         historical_df (pd.DataFrame): DataFrame with historical price data for volatility calculation.

#     Returns:
#         pd.DataFrame: A DataFrame with future dates and simulated prices.
#     """
#     log_returns = np.log(historical_df["PriceUSD"] / historical_df["PriceUSD"].shift(1))
#     mu = log_returns.mean() * 0.3
#     sigma = log_returns.std() * 0.15

#     max_daily_drop, max_daily_gain = 0.03, 0.03
#     price_floor, price_ceiling = 80000, 150000

#     future_dates = pd.date_range(start=start_date, periods=forecast_days)
#     future_prices = np.zeros(forecast_days)
#     future_prices[0] = start_price

#     for t in range(1, forecast_days):
#         Z = np.random.standard_normal()
#         daily_return = mu - 0.5 * sigma**2 + sigma * Z
#         daily_return = np.clip(
#             daily_return, np.log(1 - max_daily_drop), np.log(1 + max_daily_gain)
#         )
#         future_prices[t] = future_prices[t - 1] * np.exp(daily_return)
#         future_prices[t] = np.clip(future_prices[t], price_floor, price_ceiling)

#     forecast_df = pd.DataFrame({"PriceUSD": future_prices}, index=future_dates)
#     forecast_df.index.name = "time"
#     forecast_df["Type"] = "Forecast"
#     return forecast_df


@st.cache_data(ttl=3600, show_spinner=False)
def load_bitcoin_data():
    """
    Loads, cleans, and combines historical, current, and forecasted Bitcoin data.
    This function creates a single, clean DataFrame as the foundation for the app.
    """
    try:
        # --- Step 1: Load All Historical Data ---
        url = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        all_data = pd.read_csv(
            StringIO(response.text),
            index_col="time",
            parse_dates=True,
            usecols=["time", "PriceUSD"],  # Only load what you need
        )
        all_data.index = all_data.index.normalize().tz_localize(None)
        all_data = all_data[~all_data.index.duplicated(keep="last")].sort_index()

        if "PriceUSD" not in all_data.columns:
            st.error("Data missing 'PriceUSD' column")
            return None

        # --- Step 2: Separate Historical Data (ends yesterday) ---
        historical_df = all_data.loc[
            BACKTEST_START : TODAY - pd.DateOffset(days=1)
        ].copy()
        historical_df["Type"] = "Historical"
        print(
            f"Historical data range: {historical_df.index.min()} to {historical_df.index.max()}"
        )

        # --- Step 3: Get Today's Price and Create Today's Data Point ---
        current_price = get_current_btc_price()
        last_known_price = historical_df["PriceUSD"].iloc[-1]

        if current_price is None:
            print("Warning: Live price fetch failed. Using last known price for today.")
            current_price = last_known_price

        today_df = pd.DataFrame(
            {"PriceUSD": [current_price], "Type": ["Today"]},
            index=pd.Index([TODAY], name="time"),
        )
        print(
            f"Today's data point created for {TODAY} with price ${current_price:,.2f}"
        )

        # --- Step 4: Generate Future Data (starts tomorrow) ---
        forecast_start_date = TODAY + pd.DateOffset(days=1)
        # future_df = generate_future_data(
        #     start_price=current_price,
        #     start_date=forecast_start_date,
        #     forecast_days=MAX_FORECAST_DAYS,
        #     historical_df=historical_df,
        # )
        # print(
        #     f"Forecast data range: {future_df.index.min()} to {future_df.index.max()}"
        # )

        # --- Step 5: Combine and Return ---
        combined_df = pd.concat([historical_df, today_df])  # , future_df])
        # Re-assign Type for clarity in charts where 'Today' is part of the historical line
        combined_df["Type"] = np.where(
            combined_df.index > TODAY, "Forecast", "Historical"
        )

        return combined_df.dropna()

    except requests.exceptions.RequestException as e:
        st.error(f"Network error loading Bitcoin data: {e}")
        return None
    except Exception as e:
        st.error(f"Error processing Bitcoin data: {e}")
        return None
