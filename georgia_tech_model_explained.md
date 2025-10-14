Of course! As a seasoned data scientist, I'd be happy to walk you through this Jupyter notebook. We're looking at a framework for backtesting a Bitcoin investment strategy. Backtesting is like using a time machine to see how your strategy would have performed on historical data.

Let's break it down, cell by cell.

### Cell 1: Framework Boilerplate - Global Variables
```python
# 🚫 DO NOT MODIFY: Framework boilerplate cell
# ---------------------------
# core/config.py
# ---------------------------

# ╔═════════════════════╗
# ║  Global Variables   ║
# ╚═════════════════════╝


# Back-test date range
BACKTEST_START     = '2011-06-01'
BACKTEST_END       = '2025-06-01'

# Rolling window length (in months)
INVESTMENT_WINDOW  = 12

# Step frequency for window start-dates: 'Daily', 'Weekly' or 'Monthly'
PURCHASE_FREQ      = 'Daily'

# Minimum per-period weight (to avoid zero allocations)
MIN_WEIGHT         = 1e-5


PURCHASE_FREQ_TO_OFFSET = {
    'Daily':   '1D',
    'Weekly':  '7D',
    'Monthly': '1M',
}
```

**Explanation:**

Think of this cell as the **"Settings" or "Configuration" panel** for our experiment. Before we run any analysis, we need to define the fundamental rules.

*   `BACKTEST_START` and `BACKTEST_END`: This is the historical period we're interested in. We're telling our code to only look at Bitcoin data from June 1, 2011, to June 1, 2025.
*   `INVESTMENT_WINDOW`: This sets the duration for each investment cycle we want to test. Here, it's set to 12 months. The code will analyze the performance over many overlapping 12-month periods within our backtest range.
*   `PURCHASE_FREQ`: This defines how often we pretend to buy Bitcoin within each 12-month window. 'Daily' means our strategy will make a decision every single day.
*   `MIN_WEIGHT`: This is a safety measure. It's a very small number (`0.00001`) that ensures our strategy never allocates exactly zero money on any given day. This can prevent mathematical errors and ensures we're always "in the market."
*   `PURCHASE_FREQ_TO_OFFSET`: This is a helper dictionary. It translates the human-friendly settings (like 'Daily') into a format that the `pandas` data analysis library understands (like '1D' for "one day").

---

### Cell 2: Extract BTC data from CoinMetrics
```python
# 🚫 DO NOT MODIFY: Framework boilerplate cell
# ---------------------------
# Extract BTC data from CoinMetrics and save locally
# ---------------------------
import pandas as pd
# ... other imports ...
def extract_btc_data_to_csv(local_path='btc_data.csv'):
    # ...
    url = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"
    response = requests.get(url)
    # ...
    btc_df = pd.read_csv(StringIO(response.text))

    btc_df['time'] = pd.to_datetime(btc_df['time']).dt.normalize()
    btc_df['time'] = btc_df['time'].dt.tz_localize(None)
    btc_df.set_index('time', inplace=True)
    # ...
    btc_df.to_csv(local_path)
    # ...

btc_df = extract_btc_data_to_csv("btc_data.csv")
```

**Explanation:**

This cell is our **Data Collector**. Its job is to go out to the internet, grab historical Bitcoin data, clean it up a little, and save it to a local file.

1.  **Import Libraries**: It starts by importing necessary tools. `pandas` is the number one library for data manipulation in Python, and `requests` is used to download files from the web.
2.  **Define the Function**: The code is wrapped in a function called `extract_btc_data_to_csv`.
3.  **Get the Data**: It uses `requests.get(url)` to download a CSV file containing daily Bitcoin data from a public repository on GitHub.
4.  **Load into a DataFrame**: `pd.read_csv` takes the downloaded text and loads it into a `DataFrame`, which is essentially a smart spreadsheet or table that `pandas` can work with.
5.  **Clean the Dates**: The next few lines are crucial data cleaning steps:
    *   `pd.to_datetime`: It converts the 'time' column from simple text into a proper date format.
    *   `.dt.normalize()`: This removes the time-of-day information (like 14:30:00), leaving just the date (e.g., 2024-10-20). For daily analysis, the time is irrelevant.
    *   `.dt.tz_localize(None)`: This removes any timezone information to keep things simple and consistent.
6.  **Set the Index**: `set_index('time', inplace=True)` is very important. It makes the date column the "row label" for our data table. This makes looking up data for a specific date incredibly fast and easy.
7.  **Save Locally**: `btc_df.to_csv(local_path)` saves our cleaned DataFrame to a file named `btc_data.csv`. This is efficient because we only need to download the data once. The next time we run the notebook, we can just load it from this file.

---

### Cell 3: Data Loading and Validation
```python
# 🚫 DO NOT MODIFY: Framework boilerplate cell
# ---------------------------
# core/data.py
# ---------------------------
# ... imports and logging ...
def load_data():
    df = pd.read_csv("btc_data.csv", index_col=0, parse_dates=True)
    df = df.loc[~df.index.duplicated(keep='last')]
    df = df.sort_index()
    return df

def validate_price_data(df):
    if df.empty or 'PriceUSD' not in df.columns:
        raise ValueError("Invalid BTC price data.")
    # ... more checks ...

# Global Variable to use later
df = load_data()
```

**Explanation:**

This cell acts as the **Quality Control Inspector**. After downloading the data, we need to load it into our main workspace and double-check that it's usable.

*   `load_data()`: This function's purpose is to read the `btc_data.csv` file we saved in the previous step.
    *   `index_col=0, parse_dates=True`: This tells pandas that the first column is our date index and it should be read as dates.
    *   `~df.index.duplicated(keep='last')`: This is a data sanity check. It looks for any duplicate dates in our data and, if it finds any, keeps only the last entry for that date. This ensures each date is unique.
    *   `sort_index()`: This sorts the data chronologically, which is essential for any time-based analysis.
*   `validate_price_data(df)`: This function is a set of checks to prevent errors later. It confirms that the data isn't empty, that it contains the all-important 'PriceUSD' column, and that the index is correctly formatted as dates.
*   `df = load_data()`: This line is the action step. It calls the `load_data` function and stores the cleaned, validated, and sorted data in a global DataFrame called `df`, which will be used in all subsequent cells.

---

### Cell 4: Core Logic - Helper and SPD Computation
```python
# ...
def _make_window_label(...):
    # ...

def compute_cycle_spd(
    dataframe: pd.DataFrame,
    strategy_function
) -> pd.DataFrame:
    # 1) Precompute full-history features & restrict to backtest
    full_feat = construct_features(dataframe).loc[BACKTEST_START:BACKTEST_END]

    # 2) Window parameters
    # ...
    results = []
    for window_start in pd.date_range(...):
        # ...
        inv_price   = (1.0 / price_slice) * 1e8  # sats per dollar

        # Compute weights on this slice
        weight_slice = strategy_function(feat_slice)

        # Uniform vs. dynamic SPD
        uniform_spd = inv_price.mean()
        dynamic_spd = (weight_slice * inv_price).sum()

        # ... calculate percentiles ...
        results.append({ ... })

    return pd.DataFrame(results).set_index("window")

```

**Explanation:**

This is the **Engine Room** of the entire notebook. The `compute_cycle_spd` function does the heavy lifting of running the backtest. It simulates the investment strategy over many overlapping time periods.

*   **Concept: Sats-per-Dollar (SPD)**: This is our key performance metric. Instead of just tracking price, we track how many "Sats" (the smallest unit of Bitcoin) we get for every dollar we invest. Buying at a low price gives you a high SPD. Our goal is to maximize this.

*   **The Loop**: The function loops through every possible start date for our 12-month `INVESTMENT_WINDOW`. For each window, it does the following:
    1.  **Slice the Data**: It takes a 12-month chunk of the price data.
    2.  **Calculate Daily SPD**: It calculates the `inv_price`, which is the Sats-per-Dollar for each day in that window.
    3.  **Get Strategy Weights**: It calls a `strategy_function` (which *you*, the user, will define later). This function is the "brain" of your strategy. It looks at the data and decides how much to invest each day. This decision is represented as a "weight."
    4.  **Compare Two Strategies**:
        *   `uniform_spd`: This represents a simple "Dollar Cost Averaging" (DCA) strategy, where you invest the exact same amount every day. Its SPD is just the average SPD over the window.
        *   `dynamic_spd`: This is the performance of *your* strategy. It's a weighted average of the daily SPD, using the weights your strategy function provided. The hope is that your strategy assigns higher weights (invests more) on days with higher SPD (lower prices).
    5.  **Calculate Percentiles**: It then calculates where your performance and the uniform performance fall on a scale from the worst possible SPD (`min_spd`) to the best possible (`max_spd`) within that window.
    6.  **Store Results**: It saves all these metrics for the window and moves to the next one.

Finally, it returns a `DataFrame` containing the performance results for every single window it tested.

---

### Cell 5: Backtest Wrapper - Aggregating Results
```python
def backtest_dynamic_dca(
    dataframe: pd.DataFrame,
    strategy_function,
    *,
    strategy_label: str = "strategy"
) -> pd.DataFrame:
    # --- run the rolling-window SPD backtest
    spd_table   = compute_cycle_spd(dataframe, strategy_function)
    # ...

    # --- print standard aggregated metrics
    print(f"\nAggregated Metrics for {strategy_label}:")
    # ...

    # --- exponential decay weighting
    # ...
    exp_avg_spd = (dynamic_spd.values * exp_weights).sum()
    # ...
    print(f"\nExponential-Decay Average SPD: {exp_avg_spd:.2f}")

    return spd_table
```

**Explanation:**

This cell is the **Reporter**. It takes the detailed, window-by-window results from the "Engine Room" and summarizes them into a human-readable report.

1.  **Run the Backtest**: It starts by calling `compute_cycle_spd` to get the raw performance data.
2.  **Print Simple Stats**: It calculates basic statistics like the minimum, maximum, mean, and median performance of your strategy across all the tested windows. This gives you a quick overview: "How good was my strategy on average? What were its best and worst periods?"
3.  **Calculate Exponential-Decay Average**: This is a more advanced and very clever metric. Instead of treating all windows equally, it gives more importance to the *most recent* windows. The logic is that performance in 2024 is probably more relevant than performance in 2014. It calculates a weighted average where recent results matter more.

This function provides the key numbers you'll use to judge whether your strategy is a success.

---

### Cell 6: Submission Checker
```python
def check_strategy_submission_ready(
    dataframe: pd.DataFrame,
    strategy_function
) -> None:
    # ...
    # 1) Forward-leakage test
    # ...
    # 2) Weight checks per rolling window
    # ...
    # 3) Performance vs. Uniform DCA (RELAXED)
    # ...

```

**Explanation:**

This cell is the **Strict Referee**. Before you can claim your strategy is good, this function runs a series of critical tests to ensure it's valid, fair, and actually works.

1.  **Forward-Leakage Test**: This is the most important test in financial modeling. It checks if you are accidentally "cheating" by using information from the future to make decisions in the past. It does this by feeding your strategy data that's been cut off at various points in time and ensuring the historical decisions don't change. If they do, it means your strategy is seeing the future, which is impossible in the real world.
2.  **Weight Checks**: This test loops through the windows and verifies that your strategy's investment weights follow the rules: they must always be positive, they can't be *too* small (respecting `MIN_WEIGHT`), and the sum of all daily weights in a window must equal 1 (meaning you invest your full budget for that window).
3.  **Performance Check**: This is a sanity check. It ensures that your "smart" dynamic strategy beats the simple uniform DCA strategy in at least 50% of the windows. If it doesn't, it's not consistently adding value.

If your strategy fails any of these checks, this function will print error messages telling you what to fix.

---

### Cell 7 & 8: Plotting Functions
```python
# ---------------------------
# core/plots.py
# ---------------------------
# ... imports ...

def plot_features(...):
    # ...
def plot_final_weights_by_window(...):
    # ...
def plot_rolling_window_weight_sums(...):
    # ...
def plot_spd_comparison(...):
    # ...
```

**Explanation:**

These final cells are the **Visualization Suite**. Data and numbers are great, but pictures often tell a clearer story. These functions create plots to help you understand your strategy's behavior.

*   `plot_features`: This plots the Bitcoin price against the primary feature (or signal) your strategy uses. This helps you visually confirm that your strategy is identifying the market conditions you want it to.
*   `plot_final_weights_by_window`: This shows how your daily investment weights change over time. You can see if your strategy is being aggressive (high weights) or conservative (low weights) and when.
*   `plot_rolling_window_weight_sums`: This is a visual check for the "sum-to-1" rule. It should produce a boring, straight line at `y=1.0`. If it doesn't, there's a bug in your strategy.
*   `plot_spd_comparison`: This is the main results chart. It plots the performance (SPD) of your dynamic strategy (blue) against the simple uniform strategy (orange) for every window. It also shows the best and worst possible outcomes (green and red). **Visually, you want to see the blue line consistently above the orange line.**



# THE MODEL #

Now we're getting to the heart of the matter. The previous cells were the framework, the test track, and the dashboard. This code snippet is the **engine**—the actual logic that defines your unique investment strategy.

Let's break down this model with the same "experienced data scientist to novice" approach.

### The Big Picture: What is this Strategy Trying to Do?

Before diving into the code, let's understand the core idea. This is a **Dynamic "Buy the Dip" Strategy**.

Think of it like a smart shopper. On most days, they spend a normal, small amount of their budget. But when they see a big sale on something they want (i.e., the price is unusually low), they decide to spend *more* of their budget that day to take advantage of the discount. To pay for this extra spending, they consciously decide to spend a little less on all the following days.

This strategy does the same with Bitcoin. It aims to:
1.  Establish a "fair" long-term price for Bitcoin.
2.  If the current price drops significantly below that "fair" price, it invests more money.
3.  The bigger the drop, the more it invests.
4.  It "pays" for this by slightly reducing its planned investment on many future days.

Now, let's see how the code achieves this.

---

### Function 1: `construct_features` - The Signal Generator
```python
def construct_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct technical indicators used for the strategy.
    Uses only past data for calculations to avoid look-ahead bias.
    """
    df = df.copy()
    df = df[['PriceUSD']]
    past_price = df['PriceUSD'].shift(1)
    df['ma200'] = past_price.rolling(window=200, min_periods=1).mean()
    df['std200'] = past_price.rolling(window=200, min_periods=1).std()
    return df
```

**Explanation:**

This function's job is not to make decisions, but to **prepare the data and create the signals** our strategy will use. It's like a scout who analyzes the terrain and reports back.

*   `df = df.copy()`: This is a standard safety measure. It creates a copy of the data so we don't accidentally modify the original, master dataset.
*   `past_price = df['PriceUSD'].shift(1)`: This is one of the most important lines for preventing a critical error called **look-ahead bias**. It "shifts" the entire price history forward by one day. This means when we calculate the signals for "today," we are only using prices from "yesterday" and before. This realistically simulates a real-world scenario where you can't use today's closing price to decide what to do this morning.
*   `df['ma200'] = past_price.rolling(window=200, ...).mean()`: This creates our first signal: the **200-day Moving Average**.
    *   **What it is:** The average Bitcoin price over the last 200 days.
    *   **What it tells us:** Think of this as the long-term "fair" price or the prevailing trend. If the current price is above the `ma200`, the market is generally considered bullish (optimistic). If it's below, it's considered bearish (pessimistic).
*   `df['std200'] = past_price.rolling(window=200, ...).std()`: This creates our second signal: the **200-day Standard Deviation**.
    *   **What it is:** A measure of how much the price has been swinging up and down (its volatility) over the last 200 days.
    *   **What it tells us:** A high `std200` means the price has been very volatile recently. A low `std200` means it's been relatively stable. We'll use this to understand if a price drop is "normal" or "unusual."

At the end, this function returns a new table with our two key signals—long-term trend and volatility—calculated for every single day.

---

### Function 2: `compute_weights` - The Decision Maker
```python
def compute_weights(df_window: pd.DataFrame) -> pd.Series:
    # ...
```



This is the **brain of the operation**. It takes that 12-month slice of data (with the signals we just created) and decides exactly how much money to invest each day. The output is a series of "weights" that must all add up to 1.0.

Let's walk through its logic, step-by-step.

*   **Steps 1-4: Initialization**
    *   The function starts by setting up. It gets the features and defines some parameters.
    *   `base_weight = 1.0 / total_days`: This is the crucial starting point. It begins with the assumption that we will do a simple **Dollar Cost Averaging (DCA)**—investing the exact same small amount every single day.
    *   `temp_weights = np.full(total_days, base_weight)`: It creates an array to hold our daily investment weights, initially filling it with this equal `base_weight` for every day.

*   **Step 5: Speed Boost**
    *   It pulls the data out of the `pandas` DataFrame and into `numpy` arrays. This is a common trick data scientists use to make loops run much, much faster.

*   **Step 6: The Main Loop - Where the Magic Happens**
    *   The code now iterates through every single day in the 12-month window. For each day, it asks a simple question: **"Is today a special day where we should invest more?"**
    *   `if ... price >= ma200: continue`: This is the **primary trigger condition**. It says: "If the price today is *above* the 200-day average, it's not on sale. Do nothing special. Just stick with the `base_weight` and move to the next day."
    *   `z_score = (ma200 - price) / std200`: This line only runs if the price is *below* the `ma200`. This is the "buy the dip" signal!
        *   **What it is:** The Z-score measures *how many standard deviations* the current price is below the long-term average.
        *   **What it tells us:** It's a more intelligent way of measuring a "dip." A z-score of 2.0 means the price is significantly lower than usual, even accounting for its normal volatility. A bigger Z-score means a bigger, more statistically significant dip.
    *   `boosted_weight = temp_weights[day_idx] * (1 + boost_alpha * z_score)`: Here, we calculate the new, higher investment for the day. The weight is increased by an amount proportional to the `z_score`. The bigger the dip, the bigger the boost.
    *   `excess = boosted_weight - temp_weights[day_idx]`: This calculates how much *extra* we are investing today compared to our original plan.
    *   **The Redistribution:** Now for the clever part. We can't just invent money. The `excess` amount has to come from somewhere.
        *   `redistribution_indices = ...`: The code identifies all the days in the *last 6 months* of the investment window.
        *   `per_day_reduction = excess / redistribution_indices.size`: It calculates a tiny amount to "subtract" from the budget of each of those future days.
        *   `if np.all(...)`: This is a final safety check. It makes sure that subtracting this tiny amount won't cause any of the future days' investments to fall below the minimum allowed (`MIN_WEIGHT`).
        *   `temp_weights[day_idx] = boosted_weight` and `temp_weights[redistribution_indices] -= ...`: If the safety check passes, the transaction is made! Today's weight is boosted, and the weights for all the days in the last 6 months are slightly reduced.

*   **Step 7: Final Output**
    *   After the loop has checked every day, the final `temp_weights` array, containing our dynamic investment plan, is put back into a `pandas.Series` and returned.

This strategy is a great example of a rules-based, quantitative approach that is both simple in concept ("buy the dip") and robust in execution (using Z-scores for signals and careful redistribution to manage the budget).