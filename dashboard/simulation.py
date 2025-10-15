# simulation.py
import pandas as pd


def update_bayesian_belief(prior_mean, prior_var, observation, obs_var):
    """
    Perform Bayesian update given new observation.
    """
    posterior_var = 1 / (1 / prior_var + 1 / obs_var)
    posterior_mean = posterior_var * (prior_mean / prior_var + observation / obs_var)
    return posterior_mean, posterior_var


def calculate_sats_per_dollar(price):
    """Convert USD price to sats per dollar (SPD)"""
    return (1.0 / price) * 1e8


def simulate_accumulation(df_window, weights, budget, current_day):
    """
    Simulate Bitcoin accumulation given weights and budget.
    """
    results = []
    total_btc = 0
    total_spent = 0
    cumulative_spd = 0

    for i in range(min(current_day + 1, len(df_window))):
        date = df_window.index[i]
        price = df_window.iloc[i]["PriceUSD"]
        weight = weights.iloc[i]

        amount_to_spend = budget * weight
        btc_bought = amount_to_spend / price if price > 0 else 0
        total_btc += btc_bought
        total_spent += amount_to_spend

        portfolio_value = total_btc * price
        pnl = portfolio_value - total_spent
        pnl_pct = (pnl / total_spent * 100) if total_spent > 0 else 0

        daily_spd = calculate_sats_per_dollar(price)
        weighted_spd = weight * daily_spd
        cumulative_spd += weighted_spd

        avg_entry = total_spent / total_btc if total_btc > 0 else 0

        remaining_weight_sum = (
            weights.iloc[i + 1 :].sum() if i + 1 < len(weights) else 0
        )
        remaining_budget = budget * remaining_weight_sum

        results.append(
            {
                "Date": date,
                "Price": price,
                "Weight": weight,
                "Amount_Spent": amount_to_spend,
                "BTC_Bought": btc_bought,
                "Total_BTC": total_btc,
                "Total_Spent": total_spent,
                "Portfolio_Value": portfolio_value,
                "Remaining_Budget": remaining_budget,
                "PnL": pnl,
                "PnL_Pct": pnl_pct,
                "Daily_SPD": daily_spd,
                "Weighted_SPD": weighted_spd,
                "Cumulative_SPD": cumulative_spd,
                "Avg_Entry_Price": avg_entry,
            }
        )

    return pd.DataFrame(results)


def calculate_uniform_dca_performance(df_window, budget, current_day):
    """Calculate performance metrics for uniform DCA strategy"""
    uniform_weight = 1.0 / len(df_window)
    uniform_weights = pd.Series(uniform_weight, index=df_window.index)
    return simulate_accumulation(df_window, uniform_weights, budget, current_day)
