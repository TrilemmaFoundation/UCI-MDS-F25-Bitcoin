# dashboard/email_helpers/daily_emailer.py
import pandas as pd
import sys
from datetime import datetime, timedelta

sys.path.append(".")

# --- Local Imports ---
import dashboard.config as config
from dashboard.data_loader import load_bitcoin_data
from dashboard.model.strategy_new import compute_weights
from dashboard.model.strategy_gt import compute_weights as compute_weights_gt
from dashboard.simulation import simulate_accumulation
from dashboard.backend.gsheet_utils import worksheet, GSHEET_ENABLED
from dashboard.email_helpers.daily_email_template import daily_btc_purchase_email
from dashboard.email_helpers.email_utils import send_email


def get_users_opted_in_for_email():
    """
    Get all users who have opted in for email (email_opted_in == 1).

    Returns:
        list: List of dictionaries containing user information.
    """
    if not GSHEET_ENABLED or worksheet is None:
        print("Google Sheets not configured, cannot retrieve users")
        return []

    try:
        # Get all values from the sheet
        all_values = worksheet.get_all_values()

        if len(all_values) < 2:
            print("No data in sheet")
            return []

        # First row is headers
        headers = all_values[0]

        # Find the index of the email_opted_in column
        try:
            email_opted_in_idx = headers.index("email_opted_in")
        except ValueError:
            print("email_opted_in column not found in sheet")
            return []

        # Get all users who have opted in (value == '1')
        opted_in_users = []
        for row in all_values[1:]:  # Skip header row
            if len(row) > email_opted_in_idx and row[email_opted_in_idx] == "1":
                user_info = {
                    "user_email": row[0] if len(row) > 0 else "",
                    "budget": float(row[1]) if len(row) > 1 and row[1] else 0,
                    "start_date": row[2] if len(row) > 2 else "",
                    "investment_period": int(row[3]) if len(row) > 3 and row[3] else 0,
                    "boost_factor": float(row[4]) if len(row) > 4 and row[4] else 1.0,
                }
                opted_in_users.append(user_info)

        print(f"Found {len(opted_in_users)} users opted in for emails")
        return opted_in_users

    except Exception as e:
        print(f"Error retrieving opted-in users: {e}")
        return []


def calculate_user_buy_amount(user_info, df_btc, model_choice="Default Model"):
    """
    Calculate the buy amount for a specific user based on their preferences.

    Args:
        user_info: Dictionary containing user preferences
        df_btc: DataFrame with Bitcoin price data
        model_choice: Which model to use for weight computation

    Returns:
        dict: Contains amount_to_invest, today_price, today_weight, and today_date
    """
    try:
        # Parse user preferences
        start_date = pd.to_datetime(user_info["start_date"])
        investment_window = (
            user_info["investment_period"] * 30
        )  # Convert months to days
        budget = user_info["budget"]
        boost_alpha = user_info["boost_factor"]

        # Create date range for this user's investment window
        end_date = start_date + pd.DateOffset(days=investment_window - 1)

        # Filter Bitcoin data for the user's window
        df_window = df_btc[
            (df_btc.index >= start_date) & (df_btc.index <= end_date)
        ].copy()

        # If we don't have enough data yet, use all available data from start_date
        if df_window.empty:
            df_window = df_btc[df_btc.index >= start_date].copy()

        if df_window.empty:
            print(f"No data available for user {user_info['user_email']}")
            return None

        # Extend df_window with future dates if needed
        last_date_in_window = df_window.index.max()
        if end_date > last_date_in_window:
            future_days_needed = (end_date - last_date_in_window).days
            future_dates = pd.date_range(
                start=last_date_in_window + pd.Timedelta(days=1),
                periods=future_days_needed,
                freq="D",
            )
            last_price = df_window["PriceUSD"].iloc[-1]
            future_df = pd.DataFrame(
                {
                    "PriceUSD": [last_price] * len(future_dates),
                    "Type": ["Future"] * len(future_dates),
                },
                index=future_dates,
            )
            df_window = pd.concat([df_window, future_df])
            df_window = df_window[~df_window.index.duplicated(keep="last")]
            df_window = df_window.sort_index()

        # Compute weights
        if model_choice == "GT-MSA-S25-Trilemma Model":
            weights = compute_weights_gt(df_window)
        else:
            weights = compute_weights(df_window, boost_alpha=boost_alpha)

        # Get today's data
        today = datetime.now().date()
        today_pd = pd.Timestamp(today)

        # Find the closest date in our data to today
        if today_pd in df_window.index:
            today_data = df_window.loc[today_pd]
            today_weight = weights.loc[today_pd]
        else:
            # Use the most recent data available
            today_data = df_window.iloc[-1]
            today_weight = weights.iloc[-1]

        today_date = today_data.name.strftime("%Y-%m-%d")
        today_price = today_data["PriceUSD"]
        amount_to_invest = budget * today_weight

        return {
            "amount_to_invest": amount_to_invest,
            "today_price": today_price,
            "today_weight": today_weight,
            "today_date": today_date,
            "user_email": user_info["user_email"],
        }

    except Exception as e:
        print(f"Error calculating buy amount for {user_info['user_email']}: {e}")
        return None


def send_email_to_user(user_email, amount_to_invest):
    """
    Send email to user with their recommended purchase amount.

    Args:
        user_email: Email address to send to
        amount_to_invest: Dollar amount to invest today
    """
    # Format amount as string with 2 decimal places
    amount_str = f"{amount_to_invest:.2f}"

    # Generate email HTML
    email_html = daily_btc_purchase_email(amount_str)

    # TODO: Implement actual email sending logic here
    # This would use your preferred email service (SendGrid, AWS SES, etc.)
    send_email(
        subject="Daily BTC Purchase", body=email_html, email_recipient=user_email
    )
    print(f"sent email to {user_email} with amount ${amount_str}")
    print(f"Email HTML length: {len(email_html)} characters")

    return True


def main():
    """Main function to email users once daily"""
    print(f"Starting daily email job at {datetime.now()}")

    # Load Bitcoin data
    print("Loading Bitcoin data...")
    df_btc = load_bitcoin_data()
    if df_btc is None or df_btc.empty:
        print("❌ Unable to load Bitcoin data. The API may be down.")
        return

    print(f"✓ Loaded Bitcoin data with {len(df_btc)} records")

    # Get all users opted in for email
    print("Retrieving users opted in for email...")
    users = get_users_opted_in_for_email()

    if not users:
        print("No users opted in for email")
        return

    # Process each user
    success_count = 0
    error_count = 0

    for user_info in users:
        print(f"\nProcessing user: {user_info['user_email']}")

        # Calculate buy amount
        result = calculate_user_buy_amount(user_info, df_btc)

        if result is None:
            print(f"  ❌ Failed to calculate buy amount")
            error_count += 1
            continue

        print(f"  ✓ Buy amount: ${result['amount_to_invest']:.2f}")
        print(f"  ✓ BTC Price: ${result['today_price']:.2f}")
        print(f"  ✓ Weight: {result['today_weight']:.4f}")

        # Send email
        if send_email_to_user(result["user_email"], result["amount_to_invest"]):
            print(f"  ✓ Email sent successfully")
            success_count += 1
        else:
            print(f"  ❌ Failed to send email")
            error_count += 1

    print(f"\n{'='*50}")
    print(f"Daily email job completed at {datetime.now()}")
    print(f"Total users processed: {len(users)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
