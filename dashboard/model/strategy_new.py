# model/strategy_new.py
"""
Dynamic Buy-The-Dip Bitcoin Accumulation Strategy

This module implements a rules-based strategy that:
1. Identifies when BTC price is below the 200-day moving average
2. Calculates statistical significance using Z-scores
3. Dynamically allocates more capital during significant dips
4. Redistributes excess allocation from future periods
5. Ensures all weights sum to 1.0 and respect minimum weight constraints
"""

import pandas as pd
import numpy as np

# Minimum weight per period (framework requirement)
MIN_WEIGHT = 1e-5


def construct_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct technical indicators used for the strategy.
    Uses only past data for calculations to avoid look-ahead bias.

    This function is CRITICAL for preventing forward-leakage:
    - Uses .shift(1) to ensure we only use yesterday's data for today's decision
    - Calculates 200-day moving average as long-term trend indicator
    - Calculates 200-day standard deviation as volatility measure

    Args:
        df: DataFrame with 'PriceUSD' column and datetime index

    Returns:
        DataFrame with added feature columns: ma200, std200
    """
    df = df.copy()

    # Ensure we have PriceUSD column
    if "PriceUSD" not in df.columns:
        raise ValueError("DataFrame must contain 'PriceUSD' column")

    df = df[["PriceUSD"]]

    # CRITICAL: Shift by 1 to avoid look-ahead bias
    # When making decision for day T, we only know prices up to day T-1
    past_price = df["PriceUSD"].shift(1)

    # Calculate 200-day moving average (long-term trend)
    df["ma200"] = past_price.rolling(window=200, min_periods=1).mean()

    # Calculate 200-day standard deviation (volatility measure)
    df["std200"] = past_price.rolling(window=200, min_periods=1).std()

    return df


def compute_weights(df_window: pd.DataFrame, boost_alpha: float = 1.25) -> pd.Series:
    """
    Given a window of price data, compute portfolio weights that sum to 1.

    Strategy Logic:
    1. Start with equal weights (uniform DCA baseline)
    2. For each day where price < MA200:
       - Calculate Z-score: (MA200 - price) / std_dev
       - Boost weight proportionally to Z-score
       - Redistribute excess from last half of window
    3. Ensure all weights >= MIN_WEIGHT
    4. Final weights sum to exactly 1.0

    Args:
        df_window: DataFrame with price data for the investment window
        boost_alpha: Multiplier for z-score boosting (default 1.25)
                    Higher values = more aggressive buying during dips

    Returns:
        Series of daily weights that sum to 1.0
    """
    # 1. Build feature DataFrame and index info
    features = construct_features(df_window)
    dates = features.index
    total_days = len(features)

    # Edge case: empty window
    if total_days == 0:
        return pd.Series(dtype=float)

    # 2. Strategy parameters
    # Rebalancing window: last half of the investment period
    rebalance_window = max(total_days // 2, 1)

    # 3. Initialize equal weights (uniform DCA baseline)
    base_weight = 1.0 / total_days
    temp_weights = np.full(total_days, base_weight, dtype=float)

    # 4. Extract numpy arrays for speed (vectorization optimization)
    price_array = features["PriceUSD"].values
    ma200_array = features["ma200"].values
    std200_array = features["std200"].values

    # 5. Main loop: Identify buy opportunities and boost weights
    for day_idx in range(total_days):
        price = price_array[day_idx]
        ma200 = ma200_array[day_idx]
        std200 = std200_array[day_idx]

        # Skip if no valid signal (missing data or price above trend)
        if pd.isna(ma200) or pd.isna(std200) or std200 == 0 or price >= ma200:
            continue

        # Calculate Z-score: How many standard deviations below MA200?
        # Higher Z-score = bigger dip = stronger buy signal
        z_score = (ma200 - price) / std200

        # Boost this day's weight proportionally to the dip magnitude
        boosted_weight = temp_weights[day_idx] * (1 + boost_alpha * z_score)
        excess = boosted_weight - temp_weights[day_idx]

        # Redistribute excess over the last half of the window
        # This ensures we don't "create money" - we take from future days
        start_redistribution = max(total_days - rebalance_window, day_idx + 1)
        redistribution_indices = np.arange(start_redistribution, total_days)

        # If no days available to redistribute from, skip this boost
        if redistribution_indices.size == 0:
            continue

        # Calculate how much to reduce each future day
        per_day_reduction = excess / redistribution_indices.size

        # Safety check: Ensure no weight falls below MIN_WEIGHT
        # This prevents mathematical errors and ensures we're always in the market
        future_weights_after_reduction = (
                temp_weights[redistribution_indices] - per_day_reduction
        )

        if np.all(future_weights_after_reduction >= MIN_WEIGHT):
            # Safe to apply the boost and redistribution
            temp_weights[day_idx] = boosted_weight
            temp_weights[redistribution_indices] -= per_day_reduction
        # else: skip this boost to maintain weight constraints

    # 6. Create pandas Series with correct index - FIX: ensure length matches
    weights = pd.Series(temp_weights, index=dates, dtype=float)

    # 7. Validation: Ensure weights sum to approximately 1.0
    weight_sum = weights.sum()
    if not np.isclose(weight_sum, 1.0, rtol=1e-5, atol=1e-8):
        # This should rarely happen with correct implementation
        # Normalize to ensure exact sum of 1.0
        weights = weights / weight_sum

    return weights


def compute_z_scores(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Z-scores for each day based on deviation from MA200.

    Z-score interpretation:
    - 0.0: Price at or above MA200 (no buy signal)
    - 0.5-1.0: Weak buy signal
    - 1.0-1.5: Moderate buy signal
    - 1.5-2.0: Strong buy signal
    - 2.0+: Very strong buy signal

    Args:
        df: DataFrame with price data

    Returns:
        Series of Z-scores (0 if price >= MA200)
    """
    features = construct_features(df)
    z_scores = pd.Series(0.0, index=df.index, dtype=float)

    for idx in range(len(df)):
        price = features.iloc[idx]["PriceUSD"]
        ma200 = features.iloc[idx]["ma200"]
        std200 = features.iloc[idx]["std200"]

        # Calculate Z-score only when all data is valid and price < MA200
        if pd.notna(ma200) and pd.notna(std200) and std200 > 0 and price < ma200:
            z_scores.iloc[idx] = (ma200 - price) / std200

    return z_scores


def get_buy_signal_strength(z_score: float) -> str:
    """
    Classify buy signal strength based on Z-score magnitude.

    Args:
        z_score: Standard deviations below MA200

    Returns:
        Signal strength classification string
    """
    if z_score >= 2.0:
        return "Very Strong"
    elif z_score >= 1.5:
        return "Strong"
    elif z_score >= 1.0:
        return "Moderate"
    elif z_score >= 0.5:
        return "Weak"
    else:
        return "None"


def calculate_portfolio_metrics(
        df_price: pd.DataFrame, weights: pd.Series, budget: float, current_day: int
) -> dict:
    """
    Calculate comprehensive portfolio performance metrics.

    Args:
        df_price: DataFrame with price data
        weights: Series of daily weights
        budget: Total budget for accumulation
        current_day: Current day index

    Returns:
        Dictionary with portfolio metrics
    """
    total_btc = 0
    total_spent = 0

    # Simulate daily purchases
    for i in range(min(current_day + 1, len(df_price))):
        price = df_price.iloc[i]["PriceUSD"]
        weight = weights.iloc[i]
        amount = budget * weight
        btc_bought = amount / price if price > 0 else 0
        total_btc += btc_bought
        total_spent += amount

    # Calculate current portfolio value
    current_price = df_price.iloc[current_day]["PriceUSD"]
    portfolio_value = total_btc * current_price

    # Calculate profit/loss
    pnl = portfolio_value - total_spent
    pnl_pct = (pnl / total_spent * 100) if total_spent > 0 else 0

    # Calculate average entry price
    avg_entry_price = total_spent / total_btc if total_btc > 0 else 0

    return {
        "total_btc": total_btc,
        "total_spent": total_spent,
        "portfolio_value": portfolio_value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "avg_entry_price": avg_entry_price,
        "current_price": current_price,
        "remaining_budget": budget - total_spent,
    }


def bayesian_update(
        prior_mean: float, prior_var: float, observation: float, obs_var: float
) -> tuple:
    """
    Perform Bayesian update given new observation.

    This implements the standard Bayesian updating formula for Gaussian distributions:
    - Posterior variance = 1 / (1/prior_var + 1/obs_var)
    - Posterior mean = posterior_var * (prior_mean/prior_var + obs/obs_var)

    As more observations are incorporated:
    - Variance decreases (confidence increases)
    - Mean converges toward observed data

    Args:
        prior_mean: Prior belief mean (expected return)
        prior_var: Prior belief variance (uncertainty)
        observation: New observation value (recent return)
        obs_var: Observation variance (measurement uncertainty)

    Returns:
        Tuple of (posterior_mean, posterior_var)
    """
    # Calculate posterior variance (precision weighting)
    posterior_var = 1 / (1 / prior_var + 1 / obs_var)

    # Calculate posterior mean (weighted average of prior and observation)
    posterior_mean = posterior_var * (prior_mean / prior_var + observation / obs_var)

    return posterior_mean, posterior_var


def get_market_regime(df: pd.DataFrame, lookback: int = 30) -> str:
    """
    Determine current market regime based on recent price action.

    Classifies market into 5 regimes based on mean return and volatility:
    - Bull Market (Low/High Vol)
    - Bear Market (Low/High Vol)
    - Sideways/Consolidation

    Args:
        df: DataFrame with price data
        lookback: Number of days to analyze (default 30)

    Returns:
        Market regime classification string
    """
    if len(df) < lookback:
        return "Insufficient Data"

    # Calculate returns for recent period
    recent = df.iloc[-lookback:]
    returns = recent["PriceUSD"].pct_change().dropna()

    # Calculate statistics
    mean_return = returns.mean()
    volatility = returns.std()

    # Classify regime
    if mean_return > 0.01 and volatility < 0.03:
        return "Bull Market (Low Vol)"
    elif mean_return > 0.01 and volatility >= 0.03:
        return "Bull Market (High Vol)"
    elif mean_return < -0.01 and volatility < 0.03:
        return "Bear Market (Low Vol)"
    elif mean_return < -0.01 and volatility >= 0.03:
        return "Bear Market (High Vol)"
    else:
        return "Sideways/Consolidation"


def validate_weights(weights: pd.Series) -> dict:
    """
    Validate that weights meet all framework requirements.

    Checks:
    1. All weights are positive
    2. All weights >= MIN_WEIGHT
    3. Weights sum to approximately 1.0

    Args:
        weights: Series of daily weights

    Returns:
        Dictionary with validation results
    """
    results = {"valid": True, "errors": [], "warnings": []}

    # Check for non-positive weights
    if (weights <= 0).any():
        results["valid"] = False
        results["errors"].append("Found non-positive weights")

    # Check minimum weight constraint
    if (weights < MIN_WEIGHT).any():
        results["valid"] = False
        results["errors"].append(f"Found weights below MIN_WEIGHT ({MIN_WEIGHT})")

    # Check sum to 1.0
    weight_sum = weights.sum()
    if not np.isclose(weight_sum, 1.0, rtol=1e-5, atol=1e-8):
        results["warnings"].append(f"Weights sum to {weight_sum:.6f} (expected 1.0)")

    return results
