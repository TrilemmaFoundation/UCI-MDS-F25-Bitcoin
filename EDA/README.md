## Bitcoin Accumulation Dashboard – Insight Analysis

This notebook analyzes how the **Bitcoin Accumulation Dashboard** and its core **Dynamic DCA** strategy support better Bitcoin investment decisions.

The Dynamic DCA framework (by **Youssef Ahmed, Georgia Tech**) achieves in our backtests:

- **Average SPD percentile:** 89.55%  
- **Win rate:** 99.41%  

both outperforming a standard uniform DCA. In the dashboard, this strategy is combined with **risk metrics**, **news sentiment**, and **MSTR purchase events**, allowing users to allocate budgets, track performance, and incorporate multiple signals through a user-friendly interface.

Despite the strong metrics, numbers alone can feel abstract—especially for beginners. This insight analysis notebook uses **EDA, visualizations, and aggregated charts** to:

- Show how well the current Bitcoin accumulation strategy actually performs.  
- Explain how the dashboard features can be used to evaluate the strategy’s decisions.  
- Illustrate how the provided information can meaningfully help investors make better Bitcoin investment choices.

### How to Reproduce the Analysis

1. **Preprocess and save data**
    Run all cells in: `Data_Preprocessing.ipynb`.
    This notebook loads the raw data, performs preprocessing, and saves the processed datasets into the `data/` directory.

2. **View the full EDA**
   The same notebook also contains the full EDA.  
   After preprocessing, continue running the remaining cells in `eda/Data_Preprocessing.ipynb` to reproduce all charts, tables, and analysis used in the insight study.
