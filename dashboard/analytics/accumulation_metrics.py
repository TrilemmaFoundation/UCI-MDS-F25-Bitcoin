# analytics/accumulation_metrics.py
"""
Accumulation Efficiency Analytics Module
Author: Analytics Team
Provides metrics to demonstrate strategy superiority over uniform DCA
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List


class AccumulationAnalyzer:
    """
    Analyzes accumulation efficiency and strategy intelligence metrics
    """

    def __init__(self, dynamic_perf: pd.DataFrame, uniform_perf: pd.DataFrame, df_window: pd.DataFrame):
        """
        Args:
            dynamic_perf: Performance data from dynamic strategy
            uniform_perf: Performance data from uniform DCA
            df_window: Price window data
        """
        self.dynamic = dynamic_perf
        self.uniform = uniform_perf
        self.prices = df_window

    def sats_advantage(self) -> Dict[str, float]:
        """
        Calculate total satoshis advantage over uniform DCA

        Returns:
            Dictionary with absolute and percentage advantage
        """
        if self.dynamic.empty or self.uniform.empty:
            return {"absolute": 0.0, "percentage": 0.0, "sats": 0}

        dynamic_btc = self.dynamic.iloc[-1]["Total_BTC"]
        uniform_btc = self.uniform.iloc[-1]["Total_BTC"]

        sats_diff = (dynamic_btc - uniform_btc) * 1e8  # Convert to satoshis
        pct_diff = ((dynamic_btc - uniform_btc) / uniform_btc * 100) if uniform_btc > 0 else 0.0

        return {
            "absolute": dynamic_btc - uniform_btc,
            "percentage": pct_diff,
            "sats": int(sats_diff)
        }

    def purchase_efficiency_scores(self) -> pd.Series:
        """
        Calculate efficiency score for each purchase (0-100)
        100 = bought at lowest price in window
        0 = bought at highest price in window

        Returns:
            Series with efficiency scores by date
        """
        if self.dynamic.empty or self.prices.empty:
            return pd.Series(dtype=float)

        min_price = self.prices["PriceUSD"].min()
        max_price = self.prices["PriceUSD"].max()

        # If all prices are the same, assign neutral score of 50
        if max_price == min_price or pd.isna(min_price) or pd.isna(max_price):
            return pd.Series([50.0] * len(self.dynamic), index=self.dynamic["Date"].values)

        # Efficiency score: lower price = higher score
        efficiency = self.dynamic.apply(
            lambda row: 100 * (1 - (row["Price"] - min_price) / (max_price - min_price)),
            axis=1
        )
        efficiency.index = self.dynamic["Date"]

        return efficiency

    def dip_capture_analysis(self) -> Dict[str, float]:
        """
        Analyze how well the strategy captures price dips

        Returns:
            Dictionary with dip capture metrics
        """
        if self.dynamic.empty or self.prices.empty:
            return {
                "dip_days": 0,
                "captured_dips": 0,
                "capture_rate": 0.0,
                "avg_dip_weight": 0.0
            }

        # Calculate rolling mean to identify dips (using 14-day window)
        rolling_mean = self.prices["PriceUSD"].rolling(window=14, min_periods=1).mean()

        # Identify dip days (price < 95% of rolling mean)
        dip_threshold = 0.95
        is_dip = self.prices["PriceUSD"] < (rolling_mean * dip_threshold)

        # Get dates where dips occurred
        dip_dates = self.prices.index[is_dip]

        # Check which dips we captured with above-average allocation
        avg_weight = self.dynamic["Weight"].mean()
        captured_dips = 0
        total_dip_weight = 0

        for date in dip_dates:
            if date in self.dynamic["Date"].values:
                weight = self.dynamic[self.dynamic["Date"] == date]["Weight"].iloc[0]
                total_dip_weight += weight
                if weight > avg_weight:
                    captured_dips += 1

        dip_count = len(dip_dates)
        capture_rate = (captured_dips / dip_count * 100) if dip_count > 0 else 0.0
        avg_dip_weight = total_dip_weight / dip_count if dip_count > 0 else 0.0

        return {
            "dip_days": dip_count,
            "captured_dips": captured_dips,
            "capture_rate": capture_rate,
            "avg_dip_weight": avg_dip_weight
        }

    def timing_intelligence_score(self) -> float:
        """
        Calculate overall timing intelligence score (0-100)
        Combines multiple efficiency metrics

        Returns:
            Overall timing score
        """
        if self.dynamic.empty:
            return 0.0

        # Component 1: Purchase efficiency (40% weight)
        efficiency_scores = self.purchase_efficiency_scores()
        avg_efficiency = efficiency_scores.mean() if not efficiency_scores.empty else 0
        # Handle potential NaN
        if pd.isna(avg_efficiency):
            avg_efficiency = 0

        # Component 2: Dip capture rate (40% weight)
        dip_metrics = self.dip_capture_analysis()
        dip_score = dip_metrics["capture_rate"]

        # Component 3: SPD advantage (20% weight)
        sats_adv = self.sats_advantage()
        # Normalize SPD advantage to 0-100 scale (assume max 50% advantage)
        # Handle negative values: clip to 0-100 range
        raw_spd_score = (sats_adv["percentage"] / 50.0) * 100
        spd_score = max(0, min(100, raw_spd_score))

        # Weighted combination
        overall_score = (avg_efficiency * 0.4) + (dip_score * 0.4) + (spd_score * 0.2)

        # Ensure score is in valid range
        return max(0.0, min(100.0, overall_score))

    def daily_efficiency_heatmap_data(self) -> pd.DataFrame:
        """
        Prepare data for calendar heatmap visualization

        Returns:
            DataFrame with date, efficiency, and metadata for each day
        """
        if self.dynamic.empty:
            return pd.DataFrame()

        efficiency_scores = self.purchase_efficiency_scores()

        # Ensure efficiency scores align with dynamic data
        if len(efficiency_scores) != len(self.dynamic):
            # Fall back to creating aligned efficiency scores
            efficiency_values = [50.0] * len(self.dynamic)
        else:
            efficiency_values = efficiency_scores.values

        heatmap_data = pd.DataFrame({
            "Date": self.dynamic["Date"].values,
            "Efficiency": efficiency_values,
            "Price": self.dynamic["Price"].values,
            "Weight": self.dynamic["Weight"].values,
            "Amount_Spent": self.dynamic["Amount_Spent"].values
        })

        # Add day of week and week number for calendar layout
        heatmap_data["DayOfWeek"] = pd.to_datetime(heatmap_data["Date"]).dt.dayofweek
        heatmap_data["Week"] = pd.to_datetime(heatmap_data["Date"]).dt.isocalendar().week
        heatmap_data["Month"] = pd.to_datetime(heatmap_data["Date"]).dt.month
        heatmap_data["Day"] = pd.to_datetime(heatmap_data["Date"]).dt.day

        return heatmap_data

    def capital_utilization(self) -> float:
        """
        Calculate how efficiently capital was deployed (% of budget used)

        Returns:
            Percentage of total budget utilized
        """
        if self.dynamic.empty:
            return 0.0

        # Assuming total budget = sum of all weights * per-day allocation
        # This is an approximation based on the weight normalization
        total_spent = self.dynamic["Total_Spent"].iloc[-1]

        # The weights should sum to 1.0 for normalized strategies
        # So total_budget should be approximately total_spent / sum(weights)
        total_weight = self.dynamic["Weight"].sum()

        if total_weight == 0:
            return 0.0

        # Capital utilization is essentially 100% if weights are normalized
        # But we can check if there's any remaining budget
        if len(self.dynamic) > 0 and "Remaining_Budget" in self.dynamic.columns:
            remaining = self.dynamic["Remaining_Budget"].iloc[-1]
            total_budget = total_spent + remaining
            utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0.0
            return utilization

        return 100.0  # Default assumption

    def top_purchases(self, n: int = 5) -> pd.DataFrame:
        """
        Identify top N most efficient purchases

        Args:
            n: Number of top purchases to return

        Returns:
            DataFrame with top purchases sorted by efficiency
        """
        if self.dynamic.empty:
            return pd.DataFrame()

        efficiency_scores = self.purchase_efficiency_scores()

        # Ensure efficiency scores align with dynamic data
        if len(efficiency_scores) != len(self.dynamic):
            # Fall back to creating aligned efficiency scores
            efficiency_values = [50.0] * len(self.dynamic)
        else:
            efficiency_values = efficiency_scores.values

        purchase_data = pd.DataFrame({
            "Date": self.dynamic["Date"].values,
            "Price": self.dynamic["Price"].values,
            "BTC_Bought": self.dynamic["BTC_Bought"].values,
            "Amount_Spent": self.dynamic["Amount_Spent"].values,
            "Efficiency": efficiency_values
        })

        # Sort by efficiency and get top N
        # Ensure n doesn't exceed available data
        n_actual = min(n, len(purchase_data))
        if n_actual == 0:
            return pd.DataFrame()

        top_n = purchase_data.nlargest(n_actual, "Efficiency")

        return top_n

    def accumulation_progress_over_time(self) -> pd.DataFrame:
        """
        Calculate cumulative advantage over time for area chart

        Returns:
            DataFrame with cumulative BTC advantage by date
        """
        if self.dynamic.empty or self.uniform.empty:
            return pd.DataFrame()

        try:
            # Merge dynamic and uniform data by date
            merged = pd.merge(
                self.dynamic[["Date", "Total_BTC", "Cumulative_SPD"]],
                self.uniform[["Date", "Total_BTC", "Cumulative_SPD"]],
                on="Date",
                suffixes=("_dynamic", "_uniform"),
                how="inner"  # Only keep matching dates
            )

            if merged.empty:
                return pd.DataFrame()

            # Calculate running advantage
            merged["BTC_Advantage"] = merged["Total_BTC_dynamic"] - merged["Total_BTC_uniform"]
            merged["Sats_Advantage"] = merged["BTC_Advantage"] * 1e8
            merged["SPD_Advantage"] = merged["Cumulative_SPD_dynamic"] - merged["Cumulative_SPD_uniform"]

            return merged[["Date", "BTC_Advantage", "Sats_Advantage", "SPD_Advantage",
                           "Total_BTC_dynamic", "Total_BTC_uniform"]]
        except Exception as e:
            # If merge fails, return empty DataFrame
            return pd.DataFrame()

    def get_all_efficiency_metrics(self) -> Dict:
        """
        Get all efficiency metrics in one call

        Returns:
            Dictionary with all key metrics
        """
        sats_adv = self.sats_advantage()
        dip_metrics = self.dip_capture_analysis()
        timing_score = self.timing_intelligence_score()
        capital_util = self.capital_utilization()

        return {
            "Sats Advantage": sats_adv["sats"],
            "BTC Advantage (%)": sats_adv["percentage"],
            "Dip Capture Rate (%)": dip_metrics["capture_rate"],
            "Timing Intelligence Score": timing_score,
            "Capital Utilization (%)": capital_util,
            "Total Dips Identified": dip_metrics["dip_days"],
            "Dips Captured": dip_metrics["captured_dips"]
        }
