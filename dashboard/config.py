# config.py
from datetime import datetime, timedelta
import pandas as pd

# ╔════════════════════════════════════════════════════════╗
# ║  Configuration Constants                               ║
# ╚════════════════════════════════════════════════════════╝

BACKTEST_START = "2011-06-01"
today_raw = datetime.today() - timedelta(days=1)
today_formatted = today_raw.strftime("%Y-%m-%d")

# This now represents the end of REAL historical data.
HISTORICAL_END = today_formatted

# New constant for future projection
MAX_FORECAST_DAYS = 365 * 2 + 1  # Project up to 2 years into the future

PURCHASE_FREQ = "Daily"
MIN_WEIGHT = 1e-5

PURCHASE_FREQ_TO_OFFSET = {
    "Daily": "1D",
    "Weekly": "7D",
    "Monthly": "1M",
}
