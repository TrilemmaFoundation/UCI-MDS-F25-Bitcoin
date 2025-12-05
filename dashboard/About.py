import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 📊 HELPER FUNCTIONS (Refactored from UCI-MDS-F25-BITCOIN/EDA/eda_code.ipynb)
# ==========================================


@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)


def get_efficiency_comparison(
    file_path="dashboard/about_eda/data/weight_price_ma20_spd_pct.csv",
):
    try:
        df = load_data(file_path)
        # Constants for calculation
        budget = 10_000.0
        cheap_pct_threshold = 30.0

        # Data prep
        price = df["PriceUSD"].astype(float).values
        dyn_w_raw = df["weight"].astype(float).values
        spd_pct = df["spd_percentile"].astype(float).values

        # Normalize weights
        dyn_w = dyn_w_raw / dyn_w_raw.sum()
        n = len(df)
        uni_w = np.full(n, 1.0 / n)

        # Calculations
        spd = 100_000_000.0 / price
        dyn_alloc = dyn_w * budget
        uni_alloc = uni_w * budget

        dyn_total_btc = (dyn_alloc / price).sum()
        uni_total_btc = (uni_alloc / price).sum()

        dyn_eff_price = budget / dyn_total_btc
        uni_eff_price = budget / uni_total_btc

        cheap_mask = spd_pct >= cheap_pct_threshold
        dyn_timing = (dyn_alloc[cheap_mask].sum() / dyn_alloc.sum()) * 100
        uni_timing = (uni_alloc[cheap_mask].sum() / uni_alloc.sum()) * 100

        summary = pd.DataFrame(
            {
                "Metric": [
                    "Total BTC Accumulated",
                    "Effective Avg Price ($/BTC)",
                    f"Capital Deployed in 'Cheap' Zone (Top {int(cheap_pct_threshold)}%)",
                ],
                "Dynamic DCA (The Model)": [
                    f"{dyn_total_btc:.4f} BTC",
                    f"${dyn_eff_price:,.2f}",
                    f"{dyn_timing:.1f}%",
                ],
                "Uniform DCA (Standard)": [
                    f"{uni_total_btc:.4f} BTC",
                    f"${uni_eff_price:,.2f}",
                    f"{uni_timing:.1f}%",
                ],
            }
        )
        return summary
    except Exception as e:
        return None


def plot_interactive_yearly_allocation(
    file_path="dashboard/about_eda/data/weight_price.csv", year=2022
):
    try:
        df = load_data(file_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # Window: June 1 -> May 31
        start_date = pd.Timestamp(f"{year}-06-01")
        end_date = pd.Timestamp(f"{year+1}-05-31")

        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        df_filtered = df[mask]

        if df_filtered.empty:
            return None

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # BTC Price (Line)
        fig.add_trace(
            go.Scatter(
                x=df_filtered["date"],
                y=df_filtered["PriceUSD"],
                mode="lines",
                name="BTC Price",
                line=dict(color="#1f77b4"),
            ),
            secondary_y=False,
        )

        # Allocation Weight (Bar)
        fig.add_trace(
            go.Bar(
                x=df_filtered["date"],
                y=df_filtered["weight"],
                name="Daily Buy Amount",
                marker=dict(color="red", opacity=0.6),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title=f"Strategy in Action: Price vs. Buying Behavior ({year}-{year+1})",
            xaxis_title="Date",
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=20, r=20, t=50, b=20),
            hovermode="x unified",
        )
        fig.update_yaxes(title_text="BTC Price ($)", secondary_y=False)
        fig.update_yaxes(
            title_text="Allocation Weight", secondary_y=True, showgrid=False
        )

        return fig
    except Exception as e:
        return None


def plot_regime_behavior(file_path="dashboard/about_eda/data/weight_price_ma20.csv"):
    try:
        df = load_data(file_path)
        df["date"] = pd.to_datetime(df["date"])

        price = df["PriceUSD"]
        ma = df["MA20"]
        buffer = 0.05

        conditions = [
            price > ma * (1 + buffer),
            price < ma * (1 - buffer),
        ]
        choices = ["Bull (Expensive)", "Bear (Cheap)"]
        df["regime"] = np.select(conditions, choices, default="Sideways")

        regime_alloc = df.groupby("regime")["weight"].mean()

        # Plot
        fig, ax = plt.subplots(figsize=(6, 3))
        colors = ["red" if r == "Bear (Cheap)" else "gray" for r in regime_alloc.index]
        regime_alloc.plot(kind="bar", ax=ax, color=colors)
        ax.set_title("Average Daily Allocation by Market Condition")
        ax.set_ylabel("Allocation Amount")
        ax.set_xlabel("")
        plt.xticks(rotation=0)
        return fig
    except Exception as e:
        return None


def plot_spd_boxplot(
    file_path="dashboard/about_eda/data/weight_price_ma20_spd_pct.csv",
):
    try:
        df = load_data(file_path)
        df = df.dropna(subset=["spd_percentile", "weight"])
        bucket_size = 20
        bins = list(range(0, 100 + bucket_size, bucket_size))
        df["bucket"] = pd.cut(df["spd_percentile"], bins=bins)

        # Prepare data for plotting
        buckets = []
        labels = []
        means = []

        for name, group in df.groupby("bucket", observed=True):
            buckets.append(group["weight"].values)
            labels.append(str(name))
            means.append(group["weight"].mean())

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.boxplot(buckets, tick_labels=labels, showfliers=False)

        # Add means
        x_positions = range(1, len(labels) + 1)
        ax.plot(x_positions, means, "ro", label="Mean Allocation")

        ax.set_yscale("log")
        ax.set_title("Allocation Size vs. How 'Good' the Deal Is (SPD Percentile)")
        ax.set_xlabel("SPD Percentile Bucket (Higher = Better Deal)")
        ax.set_ylabel("Allocation Size (Log Scale)")
        ax.legend()
        return fig
    except Exception as e:
        return None


# ==========================================
# 📝 MAIN PAGE CONTENT
# ==========================================

md_intro = """
# Welcome to Your Smart Bitcoin Accumulator! 📊

Hello and welcome! If you're new to Bitcoin, you've probably asked the biggest question everyone has: **"When is the right time to buy?"**

The price of Bitcoin can seem unpredictable. This dashboard is designed to help you navigate that question by turning a complex decision into a simple, automated plan.

Our goal is simple: to help you accumulate Bitcoin for the long term in an intelligent way, removing the stress and guesswork.

---

### 1. The "Secret Sauce": Smart Shopper Model 🧠

**Credit:** *Model developed by Youssef Ahmed, Georgia Institute of Technology.*

Instead of trying to "time the market" perfectly, the model follows a disciplined strategy. Imagine you're a **Smart Shopper** with a weekly grocery budget.

🛒 **Strategy A: The Steady Approach (Uniform DCA)**
You spend the exact same amount every day. This is safe and consistent.

💡 **Strategy B: The *Smart Shopper* Approach (Dynamic DCA)**
What if your favorite item goes on a **huge sale**? A smart shopper would spend *more* to stock up while the price is low, and spend *less* when the price is high.

**The model does exactly this for Bitcoin:**
1.  **Establishes a "Fair Price":** Calculates the long-term trend.
2.  **Looks for a "Sale":** Uses a metric called **SPD** (Spending Power). High SPD = Bitcoin is cheap.
3.  **Buys More on Sale:** Automatically allocates a larger budget on "sale" days.

---
"""

st.markdown(md_intro)

st.header("2. Does It Actually Work? (The Data) 📈")
st.write(
    "We analyzed the strategy's performance historically to see if this logic results in more Bitcoin."
)

# --- CHART: EFFICIENCY TABLE ---
st.subheader("🏆 Dynamic DCA vs. Uniform DCA")
st.write(
    "We compared this Dynamic strategy against buying the exact same amount every day with the same total budget."
)

eff_df = get_efficiency_comparison()
if eff_df is not None:
    st.table(eff_df)
else:
    st.warning("⚠️ Data for efficiency comparison not found.")

st.markdown(
    """
*   **More Bitcoin:** The model accumulates significantly more BTC for the same budget.
*   **Lower Price:** It achieves a much lower average cost basis.
*   **Smart Timing:** Almost all capital is deployed when Bitcoin is historically "cheap."
"""
)

st.divider()

# --- CHART: INTERACTIVE YEARLY ---
st.subheader("🕵️‍♂️ See the Strategy in Action")
st.write(
    "Select a year below to see how the model behaves day-to-day. Notice how the **Red Bars (Buys)** get taller when the **Blue Line (Price)** drops."
)

year_select = st.selectbox(
    "Select Year to Visualize:", [2018, 2019, 2020, 2021, 2022, 2023], index=4
)
fig_yearly = plot_interactive_yearly_allocation(year=year_select)

if fig_yearly:
    st.plotly_chart(fig_yearly, use_container_width=True)
else:
    st.info("Visual data not available for the selected year.")

st.divider()

# --- CHART: REGIMES & SPD ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🐻 Bull vs. Bear Behavior")
    st.write("Does the model actually buy more in downturns?")
    fig_regime = plot_regime_behavior()
    if fig_regime:
        st.pyplot(fig_regime)
    else:
        st.write("Data not available.")
    st.caption("The model buys significantly more (tall bar) during 'Bear' markets.")

with col2:
    st.subheader("🏷️ Buying the 'Sale'")
    st.write("Does it spend more when the deal is better?")
    fig_spd = plot_spd_boxplot()
    if fig_spd:
        st.pyplot(fig_spd)
    else:
        st.write("Data not available.")
    st.caption(
        "As SPD Percentile increases (Better Deal), the allocation size (Red Dot) grows exponentially."
    )

st.markdown(
    """
---

### 3. Beyond the Math: Market Context 📰

While the math handles the money, the dashboard provides context to help you stay calm:
*   **Risk Metrics:** We visualize Drawdowns so you understand potential "pain" periods.
*   **News Sentiment:** See if negative news aligns with buying opportunities.
*   **Institutional Signals:** We track MicroStrategy (MSTR) purchases.

---

### 4. Limitations & Transparency ⚠️

No model is perfect. Here are the known limitations:
1.  **Lagging Signals:** Features like MSTR signals are often reported after the fact.
2.  **Fixed Window:** The strategy optimizes based on a 365-day rolling window.
3.  **Fees:** Backtests do not account for exchange fees.
4.  **Not Financial Advice:** This tool demonstrates a quantitative strategy. **Bitcoin is highly volatile.**

**Happy accumulating!**
"""
)
