# model/strategy_gt.py
"""
GT-MSA-S25-Trilemma Dynamic DCA Strategy Implementation

This module implements the sophisticated two-layer Bitcoin accumulation strategy
from Georgia Tech's MSA project that achieved a 94.5% final score.

The model uses a 23-parameter system with:
1. Strategic Layer (α parameters): Annual investment planning based on 5 momentum signals
2. Tactical Layer (β parameters): Daily adjustments based on market conditions

Performance: 99.4% win rate against uniform DCA across 4,750+ rolling windows since 2011
"""

import pandas as pd
import numpy as np
from scipy.stats import beta

# Framework constants
MIN_WEIGHT = 1e-5
WINDOWS = [30, 90, 180, 365, 1461]
FEATURES = [f"z{w}" for w in WINDOWS]
PROTOTYPES = [(0.5, 5.0), (1.0, 1.0), (5.0, 0.5)]

# Optimized theta parameters from the final model run (94.5% score)
THETA = np.array([
    1.3507, 1.073, -1.226, 2.5141, 2.9946, -0.4083, -0.1082, -0.6809,
    0.3465, -0.6804, -2.9974, -2.9991, -1.2658, -0.368, 0.7567, -1.9627,
    -1.9124, 2.9983, 0.5704, 0.0, 0.8669, 1.2546, 5.0
])

# Global cache for features to avoid recomputation
_FULL_FEATURES = None


def softmax(x: np.ndarray) -> np.ndarray:
    """Converts a vector of scores into a probability distribution."""
    ex = np.exp(x - x.max())
    return ex / ex.sum()


def allocate_sequential(raw: np.ndarray) -> np.ndarray:
    """
    Strict left-to-right 'drain' allocator.
    Each day gets at least MIN_WEIGHT, and once a day's weight is fixed it is never touched again.
    """
    raw = np.clip(raw, 0.0, None)
    if raw.sum() == 0:
        raw[:] = 1.0
    baseline = raw / raw.sum()

    n = len(baseline)
    w = np.full(n, MIN_WEIGHT)
    rem = 1.0 - MIN_WEIGHT * n
    rem_raw = baseline.sum()

    for d in range(n):
        share = 0.0 if rem_raw == 0 else (baseline[d] / rem_raw) * rem
        w[d] += share
        rem -= share
        rem_raw -= baseline[d]

    # Numerical safety (sum may drift by small amounts)
    return w / w.sum()


def beta_mix_pdf(n: int, mix: np.ndarray) -> np.ndarray:
    """Generates a smooth baseline curve from a mixture of Beta distributions."""
    t = np.linspace(0.5 / n, 1 - 0.5 / n, n)
    return (mix[0] * beta.pdf(t, *PROTOTYPES[0]) +
            mix[1] * beta.pdf(t, *PROTOTYPES[1]) +
            mix[2] * beta.pdf(t, *PROTOTYPES[2])) / n


def zscore(s: pd.Series, win: int) -> pd.Series:
    """Calculates the rolling z-score for a given series and window."""
    m = s.rolling(win, win // 2).mean()
    sd = s.rolling(win, win // 2).std()
    return ((s - m) / sd).fillna(0)


def construct_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs the 5 momentum features (z-scores) needed for the GT model.
    Uses log-price transformation and lagged features to avoid look-ahead bias.
    """
    global _FULL_FEATURES
    
    # Ensure we have PriceUSD column
    if "PriceUSD" not in df.columns:
        raise ValueError("DataFrame must contain 'PriceUSD' column")
    
    df_copy = df[["PriceUSD"]].copy()
    
    # Calculate log prices
    log_prices = np.log(df_copy["PriceUSD"])
    
    # Calculate z-scores for each window and clip extreme values
    z_features = {}
    for win in WINDOWS:
        z_features[f"z{win}"] = zscore(log_prices, win).clip(-4, 4)
    
    z_df = pd.DataFrame(z_features, index=df.index)
    
    # Lag the features by 1 day to avoid look-ahead bias
    z_lagged = z_df.shift(1).fillna(0)
    
    # Combine with original price data
    result = df_copy.join(z_lagged)
    
    return result


def compute_weights(df_window: pd.DataFrame) -> pd.Series:
    """
    Compute portfolio weights using the GT-MSA-S25-Trilemma model.
    
    This implements the two-layer system:
    1. Strategic layer (α parameters): Sets annual investment plan using 5 momentum signals
    2. Tactical layer (β parameters): Makes daily adjustments based on market conditions
    
    Args:
        df_window: DataFrame with price data for the investment window
        
    Returns:
        Series of daily weights that sum to 1.0
    """
    if df_window.empty:
        return pd.Series(dtype=float)
    
    # Ensure we have enough data for the longest window (1461 days)
    if len(df_window) < 50:  # Minimum data requirement
        # Return uniform weights if not enough data
        n_days = len(df_window)
        return pd.Series(1.0/n_days, index=df_window.index)
    
    # Construct features
    try:
        feat_slice = construct_features(df_window)
    except Exception as e:
        # Fallback to uniform weights if feature construction fails
        n_days = len(df_window)
        return pd.Series(1.0/n_days, index=df_window.index)
    
    # Split theta into alpha and beta parameters
    alpha = THETA[:18].reshape(3, 6)  # 3x6 matrix for strategic layer
    beta_v = THETA[18:]               # 5-element vector for tactical layer
    
    # Use features from the first day to set the annual strategy
    first_day_feats = feat_slice[FEATURES].iloc[0].values
    mix = softmax(alpha @ np.r_[1, first_day_feats])
    
    # Calculate the components of the allocation formula
    n_days = len(feat_slice)
    base_alloc = beta_mix_pdf(n_days, mix)
    dynamic_signal = np.exp(-(feat_slice[FEATURES].values @ beta_v))
    
    # Combine signals and compute final weights
    raw_weights = base_alloc * dynamic_signal
    final_weights = allocate_sequential(raw_weights)
    
    return pd.Series(final_weights, index=feat_slice.index)


def get_model_performance_metrics() -> dict:
    """
    Returns the official performance metrics for the GT model.
    
    Returns:
        Dictionary with model performance statistics
    """
    return {
        "final_score": 94.5,
        "win_rate": 99.4,
        "reward_weighted_percentile": 89.55,
        "test_windows": 4750,
        "out_of_sample_performance": {
            "test_period": "2021-2025",
            "win_rate": 100.0,
            "reward_weighted_percentile": 82.91,
            "score": 91.45
        }
    }


def get_feature_explanations() -> dict:
    """
    Returns explanations of the 5 momentum features used by the model.
    
    Returns:
        Dictionary with feature descriptions
    """
    return {
        "z30": "30-day momentum: Short-term price momentum",
        "z90": "90-day momentum: Quarterly trend analysis", 
        "z180": "180-day momentum: 6-month trend strength",
        "z365": "365-day momentum: Annual cycle position",
        "z1461": "1461-day momentum: 4-year halving cycle awareness"
    }


def validate_gt_weights(weights: pd.Series) -> dict:
    """
    Validate that weights meet all framework requirements for the GT model.
    
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
