import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# 1.2 Allocation vs Price Trend

# Mean allocation weight by BTC price quartile
def price_quartile_summary(file_path: str = "data/weight_price.csv", show_plot: bool = True):    
    # Load data
    df = pd.read_csv(file_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Create price quartiles
    df["price_quartile"] = pd.qcut(
        df["PriceUSD"],
        4,
        labels=["cheapest", "low", "high", "expensive"]
    )

    # Aggregate weight stats by quartile
    quart = df.groupby("price_quartile")["weight"].agg(
        ["mean", "count"]
    )

    # Plot with matplotlib
    if show_plot:
        plt.figure(figsize=(5, 3))
        plt.bar(quart.index, quart["mean"])
        plt.xlabel("Price Quartile")
        plt.ylabel("Mean Weight")
        plt.title("Mean Allocation Weight by BTC Price Quartile")
        plt.show()

    return quart


# BTC Price and Dynamic DCA Allocation under Non-overlapping 365-Days Rolling Windows (2018–2025)
def plot_weight_price_by_year(
    start_year: int,
    end_year: int | None = None,
    file_path: str = "data/weight_price.csv"
):
    # Load data
    df = pd.read_csv(file_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # If only one year is given
    if end_year is None:
        end_year = start_year + 1

    # Window: June 1 -> May 31
    start_date = pd.Timestamp(f"{start_year}-06-01")
    end_date   = pd.Timestamp(f"{end_year}-05-31")

    # Filter by window
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    # Plot
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # BTC Price (left axis)
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["PriceUSD"],
            mode="lines",
            name="BTC Price"
        ),
        secondary_y=False
    )

    # Weight (right axis)
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["weight"],
            name="Weight",
            marker=dict(color="red", opacity=1)
        ),
        secondary_y=True
    )

    # X-axis: every June 1st
    fig.update_layout(
        title=f"BTC Price and Allocation Weight ({start_year} → {end_year})",
        xaxis=dict(
            tickmode="linear",
            dtick="M12",
            tick0=f"{start_year}-06-01"
        ),
        barmode="overlay"
    )

    fig.update_yaxes(title_text="BTC Price (USD)", secondary_y=False)
    fig.update_yaxes(title_text="Weight", secondary_y=True)

    fig.show("png")


# 1.3 Allocation Behavior by Market Regime 

def plot_allocation_by_regime(
    file_path: str = "data/weight_price_ma20.csv",
    buffer: float = 0.05,
) -> pd.DataFrame:
    # Load data
    df = pd.read_csv(file_path)
    df["date"] = pd.to_datetime(df["date"])

    price = df["PriceUSD"]
    ma = df["MA20"]

    # Define regimes based on Price vs MA20 with a buffer
    conditions = [
        price > ma * (1 + buffer),  # clearly above MA20 → bull
        price < ma * (1 - buffer),  # clearly below MA20 → bear
    ]
    choices = ["bull", "bear"]

    df["regime"] = np.select(conditions, choices, default="sideways")

    # Mean allocation weight per regime
    regime_alloc = df.groupby("regime", as_index=False)["weight"].mean()

    # Plot
    plt.figure(figsize=(6, 4))
    plt.bar(regime_alloc["regime"], regime_alloc["weight"])
    plt.xlabel("Market Regime (based on MA20)")
    plt.ylabel("Mean Allocation Weight")
    plt.title("Mean Daily Allocation by Market Regime")
    plt.tight_layout()
    plt.show()

    return regime_alloc


# 2.1 SPD Percentile vs Allocation

def plot_percentile_vs_weight(
    file_path: str = "data/weight_price_ma20_spd_pct.csv",
    figsize: tuple = (6, 4),
    jitter_std: float = 0.3,
    alpha: float = 0.25
):
    # Load data
    df = pd.read_csv(file_path)

    # Convert to numeric and clean
    df["spd_percentile"] = pd.to_numeric(df["spd_percentile"], errors="coerce")
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["spd_percentile", "weight"])

    # Add jitter on x-axis
    jitter = np.random.normal(0, jitter_std, size=len(df))

    plt.figure(figsize=figsize)
    plt.scatter(
        df["spd_percentile"] + jitter,
        df["weight"],
        alpha=alpha
    )
    plt.xlabel("SPD Percentile")
    plt.ylabel("Weight")
    plt.title("SPD Percentile vs Weight (2011–2025)")
    plt.tight_layout()
    plt.show()


def plot_weight_by_spd_bucket(
    file_path: str = "data/weight_price_ma20_spd_pct.csv",
    bucket_size: int = 20
):
    """
    Plot a boxplot of weight distribution by SPD percentile buckets,
    and highlight the mean value with a red dot (log scale).
    """

    # Load data
    df = pd.read_csv(file_path)

    # Convert columns to numeric and remove NaN rows
    df["spd_percentile"] = pd.to_numeric(df["spd_percentile"], errors="coerce")
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["spd_percentile", "weight"])

    # Create percentile buckets (e.g. 0–20, 20–40, ...)
    bins = list(range(0, 100 + bucket_size, bucket_size))
    df["bucket"] = pd.cut(df["spd_percentile"], bins=bins)

    # Collect values for each bucket
    bucket_groups = []
    labels = []

    for name, group in df.groupby("bucket", observed=True):
        bucket_groups.append(group["weight"].values)
        labels.append(str(name))

    # Plot
    plt.figure(figsize=(8, 4))

    bp = plt.boxplot(
        bucket_groups,
        labels=labels,
        showfliers=True,
        showmeans=True,
        meanline=False
    )

    # Use log scale for better visibility
    plt.yscale("log")

    # Force the mean points to be red and more visible
    for m in bp["means"]:
        m.set_marker("o")
        m.set_markerfacecolor("red")
        m.set_markeredgecolor("red")
        m.set_markersize(7)

    # Add custom legend for the mean
    plt.scatter([], [], color="red", label="Mean Weight")
    plt.legend()

    plt.xticks(rotation=45)
    plt.xlabel("SPD Percentile Bucket")
    plt.ylabel("Weight (log scale)")
    plt.title("Weight Distribution by SPD Percentile Bucket (Mean Highlighted)")
    plt.tight_layout()
    plt.show()


# 2.2 Relationship Between SPD Percentile & Future Returns  

def plot_weighted_forward_returns_with_trend(
    file_path: str = "data/weight_price_ma20_spd_pct_return.csv",
    size_scale: float = 600,
    alpha: float = 0.4
):
    """
    Plot SPD Percentile vs forward returns (30d, 60d, 365d),
    where point size is scaled by allocation weight.
    Each plot also includes a linear regression trend line.
    Y-axis is shown in symlog scale to better visualize returns.
    """

    # Load data
    df = pd.read_csv(file_path)

    # Convert columns to numeric
    df["spd_percentile"] = pd.to_numeric(df["spd_percentile"], errors="coerce")
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["30d_return"] = pd.to_numeric(df["30d_return"], errors="coerce")
    df["60d_return"] = pd.to_numeric(df["60d_return"], errors="coerce")
    df["365d_return"] = pd.to_numeric(df["365d_return"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(
        subset=["spd_percentile", "weight", "30d_return", "60d_return", "365d_return"]
    )

    # Scale marker size by weight
    w = df["weight"].values
    w_scaled = (w / (w.max() + 1e-12)) * size_scale

    # X-axis values
    x = df["spd_percentile"].values

    # Create subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharex=True)

    # -------- 30D --------
    y30 = df["30d_return"].values
    coef30 = np.polyfit(x, y30, 1)
    fit30 = np.poly1d(coef30)

    axes[0].scatter(x, y30, s=w_scaled, alpha=alpha)
    axes[0].plot(x, fit30(x), color="red", linestyle="--")
    axes[0].set_title("SPD Percentile vs 30D Return (size = weight)")
    axes[0].set_xlabel("SPD Percentile")
    axes[0].set_ylabel("30D Return (symlog scale)")
    axes[0].set_yscale("symlog")

    # -------- 60D --------
    y60 = df["60d_return"].values
    coef60 = np.polyfit(x, y60, 1)
    fit60 = np.poly1d(coef60)

    axes[1].scatter(x, y60, s=w_scaled, alpha=alpha)
    axes[1].plot(x, fit60(x), color="red", linestyle="--")
    axes[1].set_title("SPD Percentile vs 60D Return (size = weight)")
    axes[1].set_xlabel("SPD Percentile")
    axes[1].set_ylabel("60D Return (symlog scale)")
    axes[1].set_yscale("symlog")

    # -------- 365D --------
    y365 = df["365d_return"].values
    coef365 = np.polyfit(x, y365, 1)
    fit365 = np.poly1d(coef365)

    axes[2].scatter(x, y365, s=w_scaled, alpha=alpha)
    axes[2].plot(x, fit365(x), color="red", linestyle="--", linewidth=0.2)
    axes[2].set_title("SPD Percentile vs 365D Return (size = weight)")
    axes[2].set_xlabel("SPD Percentile")
    axes[2].set_ylabel("365D Return (symlog scale)")
    axes[2].set_yscale("symlog")

    plt.tight_layout()
    plt.show()


# 2.3 Investment Efficiency: Dynamic vs Uniform DCA
def compare_dynamic_vs_uniform_efficiency(
    file_path: str = "data/weight_price_ma20_spd_pct.csv",
    date_col: str = "date",
    price_col: str = "PriceUSD",
    dyn_weight_col: str = "weight",
    spd_pct_col: str = "spd_percentile",
    budget: float = 10_000.0,
    cheap_pct_threshold: float = 30.0,
) -> pd.DataFrame:
    """
    Compare Dynamic DCA vs Uniform DCA efficiency.

    Metrics included:
    - Total BTC Accumulation
    - Weighted Average SPD (sats per dollar)
    - Effective Average Purchase Price ($/BTC)
    - Timing Efficiency (% of capital invested in the cheapest X% of SPD)

    Required columns in the CSV:
    - date (optional but recommended)
    - price               -> BTC price
    - dynamic_weight      -> Dynamic DCA daily weight
    - spd_percentile      -> SPD percentile (0–100)
    """

    # -----------------------------
    # Load and sort data
    # -----------------------------
    df = pd.read_csv(file_path)

    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)

    price = df[price_col].astype(float).values
    dyn_w_raw = df[dyn_weight_col].astype(float).values
    spd_pct = df[spd_pct_col].astype(float).values

    n = len(df)
    if n == 0:
        raise ValueError("DataFrame is empty.")

    # -----------------------------
    # Normalize weights
    # -----------------------------
    # Dynamic weights may not sum to 1 → normalize
    dyn_w = dyn_w_raw / dyn_w_raw.sum()

    # Uniform DCA: equal allocation every day
    uni_w = np.full(n, 1.0 / n)

    # -----------------------------
    # Compute SPD (satoshis per dollar)
    # -----------------------------
    spd = 100_000_000.0 / price  # sats per $1

    # -----------------------------
    # Daily allocation & BTC purchased
    # -----------------------------
    dyn_alloc = dyn_w * budget
    uni_alloc = uni_w * budget

    dyn_btc = dyn_alloc / price
    uni_btc = uni_alloc / price

    dyn_total_btc = dyn_btc.sum()
    uni_total_btc = uni_btc.sum()

    # -----------------------------
    # Weighted Average SPD
    # -----------------------------
    dyn_wspd = np.average(spd, weights=dyn_alloc)
    uni_wspd = np.average(spd, weights=uni_alloc)

    # -----------------------------
    # Effective Average Purchase Price
    # -----------------------------
    dyn_eff_price = budget / dyn_total_btc
    uni_eff_price = budget / uni_total_btc

    # -----------------------------
    # Timing Efficiency
    # % of capital invested in the cheapest X% of prices (SPD percentile)
    # -----------------------------
    cheap_mask = spd_pct >= cheap_pct_threshold

    dyn_timing = dyn_alloc[cheap_mask].sum() / dyn_alloc.sum()
    uni_timing = uni_alloc[cheap_mask].sum() / uni_alloc.sum()

    dyn_timing_pct = dyn_timing * 100.0
    uni_timing_pct = uni_timing * 100.0

    # -----------------------------
    # Summary table
    # -----------------------------
    summary = pd.DataFrame(
        {
            "Dynamic DCA": {
                "Total BTC Accumulation": round(dyn_total_btc, 1),
                "Weighted Avg SPD (sats per $)": round(dyn_wspd, 1),
                "Effective Avg Purchase Price ($/BTC)": round(dyn_eff_price, 1),
                f"Timing Efficiency (% capital in top {int(cheap_pct_threshold)}%)": round(dyn_timing_pct, 1),
            },
            "Uniform DCA": {
                "Total BTC Accumulation": round(uni_total_btc, 1),
                "Weighted Avg SPD (sats per $)": round(uni_wspd, 1),
                "Effective Avg Purchase Price ($/BTC)": round(uni_eff_price, 1),
                f"Timing Efficiency (% capital in top {int(cheap_pct_threshold)}%)": round(uni_timing_pct, 1),
            },
        }
    )

    return summary


# Limitation
def build_weighted_return_table_by_horizon(
    file_path: str = "data/weight_price_ma20_spd_pct_return.csv",
    horizon: int = 30,
    pct_col: str = "spd_percentile",
    weight_col: str = "weight",
    bins = (0, 20, 40, 60, 80, 100),
):
    """
    Build ONE return table for a given horizon.

    Parameters
    ----------
    file_path : str
        Path to CSV file.
    horizon : int
        Choose from 30, 60, or 365.
    pct_col : str
        Column name for SPD percentile.
    weight_col : str
        Column name for allocation weight.
    bins : tuple
        Percentile bins.

    Required columns in CSV:
    - SPD_percentile
    - weight
    - {horizon}d_return   (e.g., 30d_return, 60d_return, 365d_return)
    """

    df = pd.read_csv(file_path)

    return_col = f"{horizon}d_return"
    if return_col not in df.columns:
        raise ValueError(f"Column '{return_col}' not found in the dataframe.")

    # Create percentile buckets
    labels = [f"{bins[i]}–{bins[i+1]}%" for i in range(len(bins) - 1)]
    df["pct_bucket"] = pd.cut(df[pct_col], bins=bins, labels=labels, include_lowest=True)

    rows = []

    for bucket, g in df.groupby("pct_bucket"):
        if g.empty:
            continue

        row = {"Percentile bucket": str(bucket)}

        # Unweighted average
        row[f"Avg {return_col}"] = g[return_col].mean()

        # Weighted average
        w = g[weight_col]
        if w.sum() == 0:
            row[f"Weighted Avg {return_col}"] = np.nan
        else:
            row[f"Weighted Avg {return_col}"] = np.average(g[return_col], weights=w)

        rows.append(row)

    result = pd.DataFrame(rows)

    return result
