import pandas as pd
import numpy as np

MIN_WEIGHT = 1e-5


# from typing import Any
# from core.config import BACKTEST_START, BACKTEST_END, INVESTMENT_WINDOW, PURCHASE_FREQ, MIN_WEIGHT
# from core.plots  import _get_window_index
# from core.strategies import register_strategy  # if you use strategy registration


def construct_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct technical indicators used for the strategy.
    Uses only past data for calculations to avoid look-ahead bias.
    """
    df = df.copy()
    df = df[["PriceUSD"]]
    past_price = df["PriceUSD"].shift(1)
    df["ma200"] = past_price.rolling(window=200, min_periods=1).mean()
    df["std200"] = past_price.rolling(window=200, min_periods=1).std()
    return df


# Example Ethereum wallet address - replace with real one for actual submissions
# ETH_WALLET_ADDRESS = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"

# @register_strategy(ETH_WALLET_ADDRESS)


def compute_weights(df_window: pd.DataFrame) -> pd.Series:
    """
    Given a 12-month slice, compute portfolio weights that sum to 1.
    Whenever a day’s weight is ‘boosted’, redistribute the excess uniformly
    over the last half of the window (i.e. the final ~6 months).
    """
    # 1. Build feature DataFrame and index info
    features = construct_features(df_window)
    dates = features.index
    total_days = len(features)

    # 2. Prepare output Series
    weights = pd.Series(index=dates, dtype=float)

    # 3. Strategy parameters
    #    PURCHASE_FREQ is one of 'Daily', 'Weekly', or 'Monthly'
    freq_to_days = {"Daily": 1, "Weekly": 7, "Monthly": 30}
    # half of the window in rows = half of total_days
    rebalance_window = max(total_days // 2, 1)
    boost_alpha = 1.25

    # 4. Initialize equal weights
    base_weight = 1.0 / total_days
    temp_weights = np.full(total_days, base_weight)

    # 5. Extract numpy arrays for speed
    price_array = features["PriceUSD"].values
    ma200_array = features["ma200"].values
    std200_array = features["std200"].values

    # 6. Loop through each day
    for day_idx in range(total_days):
        price = price_array[day_idx]
        ma200 = ma200_array[day_idx]
        std200 = std200_array[day_idx]

        # skip if no valid signal
        if pd.isna(ma200) or pd.isna(std200) or std200 == 0 or price >= ma200:
            continue

        # compute how far below MA200
        z_score = (ma200 - price) / std200

        # boost this day’s weight
        boosted_weight = temp_weights[day_idx] * (1 + boost_alpha * z_score)
        excess = boosted_weight - temp_weights[day_idx]

        # redistribute excess over the last half of the window
        start_redistribution = max(total_days - rebalance_window, day_idx + 1)
        redistribution_indices = np.arange(start_redistribution, total_days)
        if redistribution_indices.size == 0:
            continue  # nothing to drain from

        per_day_reduction = excess / redistribution_indices.size

        # apply only if no one falls below MIN_WEIGHT
        if np.all(
            temp_weights[redistribution_indices] - per_day_reduction >= MIN_WEIGHT
        ):
            temp_weights[day_idx] = boosted_weight
            temp_weights[redistribution_indices] -= per_day_reduction
        # else: skip this boost but continue looping

    # 7. Assign back into a pandas Series and return
    weights.loc[dates] = temp_weights
    return weights
