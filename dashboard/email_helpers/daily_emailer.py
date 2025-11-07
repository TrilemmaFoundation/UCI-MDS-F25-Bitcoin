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


def debug_calculate_user_buy_amount(user_info, df_btc):
    """Calculate with detailed debug output - EXACTLY matching dashboard"""

    start_date = pd.to_datetime(user_info["start_date"])
    investment_window = user_info["investment_period"] * 30
    budget = user_info["budget"]

    # Calculate end date in MONTHS not days (to match dashboard)
    end_date = start_date + pd.DateOffset(months=user_info["investment_period"])

    print(f"\n{'='*60}")
    print(f"DEBUG: User Calculation for {user_info['user_email']}")
    print(f"{'='*60}")
    print(f"Start Date: {start_date}")
    print(f"Investment Period: {user_info['investment_period']} months")
    print(f"Investment Window: {investment_window} days (approx)")
    print(f"End Date: {end_date}")
    print(f"Budget: ${budget}")
    print(f"Today: {datetime.now().date()}")

    # Match dashboard logic EXACTLY from render_controls
    last_historical_date = df_btc[df_btc["Type"] == "Historical"].index.max()

    # Determine the actual start for historical data
    historical_start = max(start_date, df_btc.index.min())
    historical_end = min(end_date, last_historical_date)

    print(f"\nStep 1: Extract historical window")
    print(f"  Historical start: {historical_start}")
    print(f"  Historical end: {historical_end}")
    print(f"  Last historical date in data: {last_historical_date}")

    # Extract historical data that overlaps with our window
    if historical_start <= last_historical_date:
        df_window = df_btc.loc[historical_start:historical_end].copy()
    else:
        # Entire window is in the future
        df_window = pd.DataFrame(columns=["PriceUSD", "Type"])
        df_window.index.name = "time"

    print(f"  Initial df_window rows: {len(df_window)}")

    # Step 2: Add Future Dates if Needed
    future_needed = end_date > last_historical_date

    if future_needed:
        if start_date > last_historical_date:
            # Entire window is in the future
            future_start = start_date
            print(f"\nStep 2: Entire window in future, starting from {future_start}")
        else:
            # Window spans historical and future
            future_start = last_historical_date + pd.Timedelta(days=1)
            future_days = (end_date - future_start).days + 1
            print(
                f"\nStep 2: Extending {future_days} days into future from {future_start}"
            )

        # Create future date range
        future_dates = pd.date_range(start=future_start, end=end_date, freq="D")

        # Get last known price for future projections
        last_price = df_btc["PriceUSD"].iloc[-1]
        print(f"  Last known price: ${last_price:.2f}")

        # Create placeholder future data
        future_df = pd.DataFrame(
            {
                "PriceUSD": [last_price] * len(future_dates),
                "Type": ["Future"] * len(future_dates),
            },
            index=future_dates,
        )

        # Append future data to df_window
        df_window = pd.concat([df_window, future_df])
    else:
        print(f"\nStep 2: No future dates needed")

    print(f"\nStep 3: Final df_window")
    print(f"  Total rows: {len(df_window)}")
    print(f"  Date range: {df_window.index.min()} to {df_window.index.max()}")
    print(f"  Historical rows: {len(df_window[df_window['Type'] == 'Historical'])}")
    if "Type" in df_window.columns:
        print(f"  Future rows: {len(df_window[df_window['Type'] == 'Future'])}")

    # Step 4: Compute weights
    print(f"\nStep 4: Computing weights...")
    from dashboard.model.strategy_gt import compute_weights as compute_weights_gt

    weights = compute_weights_gt(df_window)

    print(f"  Weights computed: {len(weights)} values")
    print(f"  Weight range: {weights.min():.6f} to {weights.max():.6f}")
    print(f"  Weight sum: {weights.sum():.6f}")

    # Step 5: Find today's position in the window
    today = datetime.now().date()
    today_pd = pd.Timestamp(today)

    print(f"\nStep 5: Looking up today's data")
    print(f"  Looking for date: {today_pd}")
    print(f"  Date in df_window? {today_pd in df_window.index}")

    # Match dashboard logic for finding "current_day"
    if today_pd in df_window.index:
        today_day_index = df_window.index.get_loc(today_pd)
        print(f"  ✓ Found exact date at index {today_day_index}")
    else:
        # Find closest date to today that's in our window
        if today_pd <= df_window.index[-1]:
            valid_dates = df_window.index[df_window.index <= today_pd]
            if len(valid_dates) > 0:
                closest_date = valid_dates[-1]
                today_day_index = df_window.index.get_loc(closest_date)
                print(
                    f"  ✓ Using closest date {closest_date} at index {today_day_index}"
                )
            else:
                today_day_index = len(df_window) - 1
                print(f"  ✗ Using last date at index {today_day_index}")
        else:
            today_day_index = len(df_window) - 1
            print(f"  ✗ Using last date at index {today_day_index}")

    # Get data at the found index
    today_data = df_window.iloc[today_day_index]
    today_weight = weights.iloc[today_day_index]
    today_date = today_data.name.strftime("%Y-%m-%d")
    today_price = today_data["PriceUSD"]
    amount_to_invest = budget * today_weight

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"{'='*60}")
    print(f"Current Day Index: {today_day_index} of {len(df_window)-1}")
    print(f"Today's Date: {today_date}")
    print(f"Today's Price: ${today_price:.2f}")
    print(f"Today's Weight: {today_weight:.10f}")
    print(f"Budget: ${budget:.2f}")
    print(f"Amount to Invest: ${amount_to_invest:.10f}")
    print(f"Amount to Invest (rounded): ${amount_to_invest:.2f}")
    print(f"{'='*60}\n")

    return {
        "amount_to_invest": amount_to_invest,
        "today_price": today_price,
        "today_weight": today_weight,
        "today_date": today_date,
        "user_email": user_info["user_email"],
        "current_day_index": today_day_index,
    }


def send_email_to_user(user_email, amount_to_invest, current_price):
    """
    Send email to user with their recommended purchase amount.

    Args:
        user_email: Email address to send to
        amount_to_invest: Dollar amount to invest today
    """
    # Format amount as string with 2 decimal places
    amount_str = f"{amount_to_invest:.2f}"

    # Generate email HTML
    email_html = daily_btc_purchase_email(amount_str, current_price=current_price)

    # TODO: Implement actual email sending logic here
    # This would use your preferred email service (SendGrid, AWS SES, etc.)
    send_email(
        subject="Daily BTC Accumulation", body=email_html, email_recipient=user_email
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
        result = debug_calculate_user_buy_amount(user_info, df_btc)

        if result is None:
            print(f"  ❌ Failed to calculate buy amount")
            error_count += 1
            continue
        print(result)

        print(f"  ✓ Buy amount: ${result['amount_to_invest']:.2f}")
        print(f"  ✓ BTC Price: ${result['today_price']:.2f}")
        print(f"  ✓ Weight: {result['today_weight']:.4f}")

        # Send email
        if send_email_to_user(
            result["user_email"],
            result["amount_to_invest"],
            current_price=f"{result['today_price']:.2f}",
        ):
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
