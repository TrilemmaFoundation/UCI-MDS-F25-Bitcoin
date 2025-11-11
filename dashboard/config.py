# config.py
from datetime import datetime
import pandas as pd
import os
import pytz

# ╔════════════════════════════════════════════════════════╗
# ║  Configuration Constants: Single Source of Truth       ║
# ╚════════════════════════════════════════════════════════╝


def get_today():
    """Get current date in Pacific timezone, normalized and timezone-naive."""
    pacific = pytz.timezone("US/Pacific")
    return pd.Timestamp.now(tz="US/Pacific").normalize().tz_localize(None)


BACKTEST_START = "2011-06-01"


# Helper functions for date calculations
def get_historical_end():
    """Get the end of historical data (yesterday's close)."""
    return get_today() - pd.DateOffset(days=1)


# --- Strategy & Framework Constants ---
PURCHASE_FREQ = "Daily"
MIN_WEIGHT = 1e-5
MAX_FORECAST_DAYS = 365 * 2

PURCHASE_FREQ_TO_OFFSET = {
    "Daily": "1D",
    "Weekly": "7D",
    "Monthly": "1M",
}

# --- Environment Variables ---
GOOGLE_SHEETS_PRIVATE_KEY = os.environ.get("GOOGLE_SHEETS_PRIVATE_KEY", "")
GOOGLE_SHEETS_PRIVATE_KEY_ID = os.environ.get("GOOGLE_SHEETS_PRIVATE_KEY_ID", "")
GOOGLE_SHEETS_CLIENT_ID = os.environ.get("GOOGLE_SHEETS_CLIENT_ID", "")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
