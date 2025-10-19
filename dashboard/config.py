# config.py
from datetime import datetime
import pandas as pd
import os

# ╔════════════════════════════════════════════════════════╗
# ║  Configuration Constants: Single Source of Truth       ║
# ╚════════════════════════════════════════════════════════╝

# A single, timezone-naive, normalized timestamp for "today".
# This is the central reference point for the entire application.
TODAY = pd.Timestamp.now().normalize()

# The start date for fetching historical data.
BACKTEST_START = "2011-06-01"

# This now clearly represents the end of REAL historical data (i.e., yesterday's close).
# The data loaded will go up to, but not include, TODAY.
HISTORICAL_END = TODAY - pd.DateOffset(days=1)

# New constant for future projection, starting from tomorrow.
MAX_FORECAST_DAYS = 365 * 2  # Project up to 2 years into the future

# --- Strategy & Framework Constants ---
PURCHASE_FREQ = "Daily"
MIN_WEIGHT = 1e-5

PURCHASE_FREQ_TO_OFFSET = {
    "Daily": "1D",
    "Weekly": "7D",
    "Monthly": "1M",
}

# --- Environment Variables ---
GOOGLE_SHEETS_PRIVATE_KEY = os.environ.get("GOOGLE_SHEETS_PRIVATE_KEY", "")
GOOGLE_SHEETS_PRIVATE_KEY_ID = os.environ.get("GOOGLE_SHEETS_PRIVATE_KEY_ID", "")
GOOGLE_SHEETS_CLIENT_ID = os.environ.get("GOOGLE_SHEETS_CLIENT_ID", "")
