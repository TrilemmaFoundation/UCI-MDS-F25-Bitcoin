# analytics/portfolio_metrics.py
"""
Portfolio Analytics Module
Author: [Qunli Liu]
Provides advanced risk and performance metrics for investment strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


class PortfolioAnalyzer:
    """
    Calculate the advanced performance indicators of the investment portfolio
    """

    def __init__(self, performance_df: pd.DataFrame):
        """
        Args:
            performance_df: from the results of simulate_accumulation
        """
        self.data = performance_df
        self.returns = self._calculate_returns()

    def _calculate_returns(self) -> pd.Series:
        """Calculate the daily return rate"""
        if len(self.data) == 0:
            return pd.Series(dtype=float)

        # Using the percentage change of Portfolio_Value
        returns = self.data['Portfolio_Value'].pct_change()
        return returns.fillna(0).replace([np.inf, -np.inf], 0)

    def sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate the annualized Sharpe ratio

        Args:
            risk_free_rate: risk-free interest rate (2%)

        Returns:
            Sharpe ratio (the higher the better, >1 is considered good)
        """
        if len(self.returns) < 2:
            return 0.0

        valid_returns = self.returns.replace([np.inf, -np.inf], np.nan).dropna()

        if len(valid_returns) == 0:
            return 0.0

        excess_returns = valid_returns - risk_free_rate / 365

        if excess_returns.std() == 0 or np.isnan(excess_returns.std()):
            return 0.0

        sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(365)

        if np.isnan(sharpe) or np.isinf(sharpe):
            return 0.0

        return sharpe

    def sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate the Sortino ratio (considering only downside risk)
        """
        if len(self.returns) < 2:
            return 0.0

        valid_returns = self.returns.replace([np.inf, -np.inf], np.nan).dropna()

        if len(valid_returns) == 0:
            return 0.0

        excess_returns = valid_returns - risk_free_rate / 365
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return 10.0

        downside_std = downside_returns.std()

        if downside_std == 0 or np.isnan(downside_std):
            return 0.0

        sortino = (excess_returns.mean() / downside_std) * np.sqrt(365)

        if np.isnan(sortino) or np.isinf(sortino):
            return 0.0

        return sortino

    def max_drawdown(self) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        Calculate the maximum drawdown and the time when it occurs

        Returns:
            (Maximum Drawdown Percentage, Start Date, End Date)
        """
        portfolio_value = self.data['Portfolio_Value']

        if len(portfolio_value) == 0:
            return 0.0, pd.Timestamp.now(), pd.Timestamp.now()

        if len(portfolio_value) == 1:
            return 0.0, portfolio_value.index[0], portfolio_value.index[0]

        cumulative_max = portfolio_value.expanding().max()
        drawdown = (portfolio_value - cumulative_max) / cumulative_max

        max_dd = drawdown.min()

        if pd.isna(max_dd) or max_dd >= 0:
            return 0.0, portfolio_value.index[0], portfolio_value.index[0]

        end_date = drawdown.idxmin()

        value_before_drawdown = portfolio_value[:end_date]
        if len(value_before_drawdown) == 0:
            start_date = portfolio_value.index[0]
        else:
            start_date = value_before_drawdown.idxmax()

        return max_dd * 100, start_date, end_date

    def win_rate(self) -> float:
        """Calculate the proportion of days generating profits"""
        if len(self.data) == 0:
            return 0.0

        profitable_days = (self.data['PnL'] > 0).sum()
        return (profitable_days / len(self.data)) * 100

    def volatility(self, annualized: bool = True) -> float:
        """Calculate the volatility of the yield rate"""
        if len(self.returns) < 2:
            return 0.0

        valid_returns = self.returns.replace([np.inf, -np.inf], np.nan).dropna()

        if len(valid_returns) == 0:
            return 0.0

        vol = valid_returns.std()

        if np.isnan(vol) or np.isinf(vol):
            return 0.0

        return vol * np.sqrt(365) if annualized else vol

    def calmar_ratio(self) -> float:
        """Calculate the Calmar ratio = Annualized return / Maximum drawdown"""
        if len(self.data) == 0:
            return 0.0

        total_return = self.data.iloc[-1]['PnL_Pct']
        days = len(self.data)

        if days == 0:
            return 0.0

        annual_return = (1 + total_return / 100) ** (365 / days) - 1

        max_dd, _, _ = self.max_drawdown()

        if max_dd == 0 or abs(max_dd) < 0.01:
            return 0.0

        calmar = (annual_return * 100) / abs(max_dd)

        if np.isnan(calmar) or np.isinf(calmar):
            return 0.0

        return calmar

    def get_all_metrics(self) -> Dict[str, float]:
        """Obtain the dictionary containing all the indicators"""
        max_dd, dd_start, dd_end = self.max_drawdown()

        return {
            'Sharpe Ratio': self.sharpe_ratio(),
            'Sortino Ratio': self.sortino_ratio(),
            'Max Drawdown (%)': max_dd,
            'Drawdown Start': dd_start,
            'Drawdown End': dd_end,
            'Win Rate (%)': self.win_rate(),
            'Annual Volatility (%)': self.volatility() * 100,
            'Calmar Ratio': self.calmar_ratio(),
            'Total Return (%)': self.data.iloc[-1]['PnL_Pct'] if len(self.data) > 0 else 0.0,
            'Final Portfolio Value': self.data.iloc[-1]['Portfolio_Value'] if len(self.data) > 0 else 0.0
        }


def compare_strategies(dynamic_perf: pd.DataFrame,
                       uniform_perf: pd.DataFrame) -> pd.DataFrame:
    """
    Compare all the indicators of the two strategies
    """
    analyzer_dynamic = PortfolioAnalyzer(dynamic_perf)
    analyzer_uniform = PortfolioAnalyzer(uniform_perf)

    metrics_dynamic = analyzer_dynamic.get_all_metrics()
    metrics_uniform = analyzer_uniform.get_all_metrics()

    comparison = pd.DataFrame({
        'Dynamic Strategy': metrics_dynamic,
        'Uniform DCA': metrics_uniform
    })

    comparison['Difference'] = (
            comparison['Dynamic Strategy'] - comparison['Uniform DCA']
    )

    return comparison