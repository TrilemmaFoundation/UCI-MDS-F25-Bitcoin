# dashboard/email_helpers/daily_emailer.py
import pandas as pd
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

sys.path.append(".")

# --- Local Imports ---
import dashboard.config as config
from dashboard.data_loader import load_bitcoin_data
from dashboard.model.strategy_new import compute_weights
from dashboard.model.strategy_gt import compute_weights as compute_weights_gt
from dashboard.simulation import simulate_accumulation
from dashboard.backend.supabase_utils import (
    get_database,
    initialize_database,
    is_user_coinbased,
    get_full_user_info,
)
from dashboard.email_helpers.daily_email_template import daily_btc_purchase_email
from dashboard.email_helpers.buy_btc_confirmation import (
    make_btc_purchase_confirmation_email,
)
from dashboard.email_helpers.email_utils import send_email
from dashboard.wallet_integration.coinbase import (
    execute_purchase_for_user,
    AUTHORIZED_EMAIL,
)
from dashboard.backend.cryptography_helpers import decrypt_value, get_fernet

import os
import logging
from cryptography.fernet import Fernet


def get_keys(user_email: str):
    print("is user coinbased?", is_user_coinbased(user_email=user_email))
    if is_user_coinbased(user_email=user_email):
        user_info = get_full_user_info(user_email=user_email)
        secret = user_info["coinbase_secret_api_key"]
        client = user_info["coinbase_client_api_key"]
        decrypted_secret = decrypt_value(get_fernet(), secret)
        decrypted_client = decrypt_value(get_fernet(), client)
        to_return = {"client": decrypted_client, "secret": decrypted_secret}
        return to_return
    else:
        return False


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

db = initialize_database(url, key)


def get_users_opted_in_for_email() -> List[Dict[str, Any]]:
    """
    Get all users who have opted in for email notifications.

    Returns:
        list: List of dictionaries containing user information for opted-in users.
              Empty list if database is not configured or on error.
    """
    db = get_database()

    if not db or not db.enabled:
        logger.warning("Database not configured, cannot retrieve users")
        return []

    try:
        # Get all email subscribers using the dedicated method
        opted_in_users = db.get_all_email_subscribers()

        if not opted_in_users:
            logger.info("No users opted in for emails")
            return []

        # Convert to the expected format with proper type conversion
        formatted_users = []
        for user in opted_in_users:
            user_info = {
                "user_email": user["user_email"],
                "budget": float(user["budget"]),
                "start_date": user["start_date"],
                "investment_period": int(user["investment_period"]),
                "boost_factor": float(user["boost_factor"]),
                "coinbase_client_api_key": user["coinbase_client_api_key"],
                "coinbase_secret_api_key": user["coinbase_secret_api_key"],
            }
            formatted_users.append(user_info)

        logger.info(f"Found {len(formatted_users)} users opted in for emails")
        return formatted_users

    except Exception as e:
        logger.error(f"Error retrieving opted-in users: {e}", exc_info=True)
        return []


def debug_calculate_user_buy_amount(
    user_info: Dict[str, Any], df_btc: pd.DataFrame
) -> Optional[Dict[str, Any]]:
    """
    Calculate buy amount with detailed debug output - EXACTLY matching dashboard.

    Args:
        user_info: Dictionary containing user preferences
        df_btc: DataFrame with Bitcoin price data

    Returns:
        Dictionary with calculation results or None on error
    """
    try:
        start_date = pd.to_datetime(user_info["start_date"])
        investment_window = user_info["investment_period"] * 30
        budget = user_info["budget"]

        # Calculate end date in MONTHS not days (to match dashboard)
        end_date = start_date + pd.DateOffset(months=user_info["investment_period"])

        logger.info(f"\n{'='*60}")
        logger.info(f"DEBUG: User Calculation for {user_info['user_email']}")
        logger.info(f"{'='*60}")
        logger.info(f"Start Date: {start_date}")
        logger.info(f"Investment Period: {user_info['investment_period']} months")
        logger.info(f"Investment Window: {investment_window} days (approx)")
        logger.info(f"End Date: {end_date}")
        logger.info(f"Budget: ${budget}")
        logger.info(f"Today: {datetime.now().date()}")

        # Match dashboard logic EXACTLY from render_controls
        last_historical_date = df_btc[df_btc["Type"] == "Historical"].index.max()

        # Determine the actual start for historical data
        historical_start = max(start_date, df_btc.index.min())
        historical_end = min(end_date, last_historical_date)

        logger.info(f"\nStep 1: Extract historical window")
        logger.info(f"  Historical start: {historical_start}")
        logger.info(f"  Historical end: {historical_end}")
        logger.info(f"  Last historical date in data: {last_historical_date}")

        # Extract historical data that overlaps with our window
        if historical_start <= last_historical_date:
            df_window = df_btc.loc[historical_start:historical_end].copy()
        else:
            # Entire window is in the future
            df_window = pd.DataFrame(columns=["PriceUSD", "Type"])
            df_window.index.name = "time"

        logger.info(f"  Initial df_window rows: {len(df_window)}")

        # Step 2: Add Future Dates if Needed
        future_needed = end_date > last_historical_date

        if future_needed:
            if start_date > last_historical_date:
                # Entire window is in the future
                future_start = start_date
                logger.info(
                    f"\nStep 2: Entire window in future, starting from {future_start}"
                )
            else:
                # Window spans historical and future
                future_start = last_historical_date + pd.Timedelta(days=1)
                future_days = (end_date - future_start).days + 1
                logger.info(
                    f"\nStep 2: Extending {future_days} days into future from {future_start}"
                )

            # Create future date range
            future_dates = pd.date_range(start=future_start, end=end_date, freq="D")

            # Get last known price for future projections
            last_price = df_btc["PriceUSD"].iloc[-1]
            logger.info(f"  Last known price: ${last_price:.2f}")

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
            logger.info(f"\nStep 2: No future dates needed")

        logger.info(f"\nStep 3: Final df_window")
        logger.info(f"  Total rows: {len(df_window)}")
        logger.info(f"  Date range: {df_window.index.min()} to {df_window.index.max()}")
        logger.info(
            f"  Historical rows: {len(df_window[df_window['Type'] == 'Historical'])}"
        )
        if "Type" in df_window.columns:
            logger.info(
                f"  Future rows: {len(df_window[df_window['Type'] == 'Future'])}"
            )

        # Step 4: Compute weights
        logger.info(f"\nStep 4: Computing weights...")
        weights = compute_weights_gt(df_window)

        logger.info(f"  Weights computed: {len(weights)} values")
        logger.info(f"  Weight range: {weights.min():.6f} to {weights.max():.6f}")
        logger.info(f"  Weight sum: {weights.sum():.6f}")

        # Step 5: Find today's position in the window
        today = datetime.now().date()
        today_pd = pd.Timestamp(today)

        logger.info(f"\nStep 5: Looking up today's data")
        logger.info(f"  Looking for date: {today_pd}")
        logger.info(f"  Date in df_window? {today_pd in df_window.index}")

        # Match dashboard logic for finding "current_day"
        if today_pd in df_window.index:
            today_day_index = df_window.index.get_loc(today_pd)
            logger.info(f"  ✓ Found exact date at index {today_day_index}")
        else:
            # Find closest date to today that's in our window
            if today_pd <= df_window.index[-1]:
                valid_dates = df_window.index[df_window.index <= today_pd]
                if len(valid_dates) > 0:
                    closest_date = valid_dates[-1]
                    today_day_index = df_window.index.get_loc(closest_date)
                    logger.info(
                        f"  ✓ Using closest date {closest_date} at index {today_day_index}"
                    )
                else:
                    today_day_index = len(df_window) - 1
                    logger.info(f"  ✗ Using last date at index {today_day_index}")
            else:
                today_day_index = len(df_window) - 1
                logger.info(f"  ✗ Using last date at index {today_day_index}")

        # Get data at the found index
        today_data = df_window.iloc[today_day_index]
        today_weight = weights.iloc[today_day_index]
        today_date = today_data.name.strftime("%Y-%m-%d")
        today_price = today_data["PriceUSD"]
        amount_to_invest = budget * today_weight

        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTS:")
        logger.info(f"{'='*60}")
        logger.info(f"Current Day Index: {today_day_index} of {len(df_window)-1}")
        logger.info(f"Today's Date: {today_date}")
        logger.info(f"Today's Price: ${today_price:.2f}")
        logger.info(f"Today's Weight: {today_weight:.10f}")
        logger.info(f"Budget: ${budget:.2f}")
        logger.info(f"Amount to Invest: ${amount_to_invest:.10f}")
        logger.info(f"Amount to Invest (rounded): ${amount_to_invest:.2f}")
        logger.info(f"{'='*60}\n")

        return {
            "amount_to_invest": amount_to_invest,
            "today_price": today_price,
            "today_weight": today_weight,
            "today_date": today_date,
            "user_email": user_info["user_email"],
            "current_day_index": today_day_index,
        }

    except Exception as e:
        logger.error(
            f"Error calculating buy amount for {user_info.get('user_email', 'unknown')}: {e}",
            exc_info=True,
        )
        return None


def send_email_to_user(
    user_email: str, amount_to_invest: float, current_price: str
) -> bool:
    """
    Send email to user with their recommended purchase amount.

    Args:
        user_email: Email address to send to
        amount_to_invest: Dollar amount to invest today
        current_price: Current BTC price as string

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Format amount as string with 2 decimal places
        amount_str = f"{amount_to_invest:.2f}"

        # Generate email HTML
        email_html = daily_btc_purchase_email(amount_str, current_price=current_price)

        # Send email using configured email service
        send_email(
            subject="Daily BTC Accumulation",
            body=email_html,
            email_recipient=user_email,
        )

        logger.info(
            f"Successfully sent email to {user_email} with amount ${amount_str}"
        )
        logger.debug(f"Email HTML length: {len(email_html)} characters")

        return True

    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {e}", exc_info=True)
        return False


def main():
    """
    Main function to process daily emails for all opted-in users.
    This should be run once per day via a scheduled task (cron, etc.)
    """
    start_time = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"Starting daily email job at {start_time}")
    logger.info(f"{'='*60}")

    # Load Bitcoin data
    logger.info("Loading Bitcoin data...")
    try:
        df_btc = load_bitcoin_data()
        if df_btc is None or df_btc.empty:
            logger.error("❌ Unable to load Bitcoin data. The API may be down.")
            return

        logger.info(f"✓ Loaded Bitcoin data with {len(df_btc)} records")
    except Exception as e:
        logger.error(f"❌ Failed to load Bitcoin data: {e}", exc_info=True)
        return

    # Get all users opted in for email
    logger.info("Retrieving users opted in for email...")
    try:
        users = get_users_opted_in_for_email()
        # print(users)
    except Exception as e:
        logger.error(f"❌ Failed to retrieve users: {e}", exc_info=True)
        return

    if not users:
        logger.info("No users opted in for email. Job completed.")
        return

    logger.info(f"Processing {len(users)} users...")

    # Process each user
    success_count = 0
    error_count = 0
    purchase_count = 0
    results = []

    for user_info in users:

        user_email = user_info.get("user_email", "unknown")

        # if user_email == "smaueltown@gmail.com":

        logger.info(f"\n{'-'*50}")
        logger.info(f"Processing user: {user_email}")
        logger.info(f"{'-'*50}")
        try:
            # Calculate buy amount
            result = debug_calculate_user_buy_amount(user_info, df_btc)

            if result is None:
                logger.error(f"  ❌ Failed to calculate buy amount for {user_email}")
                error_count += 1
                results.append(
                    {
                        "user": user_email,
                        "status": "calculation_failed",
                        "error": "Unable to calculate buy amount",
                    }
                )
                continue

            logger.info(f"  ✓ Buy amount: ${result['amount_to_invest']:.2f}")
            logger.info(f"  ✓ BTC Price: ${result['today_price']:.2f}")
            logger.info(f"  ✓ Weight: {result['today_weight']:.4f}")

            # Execute purchase if this is the authorized user
            purchase_executed = False
            potential_keys = get_keys(user_email=user_email)
            # print(potential_keys)
            if potential_keys:
                # if user_email == AUTHORIZED_EMAIL:
                print(f"  → Executing Coinbase purchase for authorized user...")

                # Set dry_run=True for testing, False for real purchases
                purchase_success = execute_purchase_for_user(
                    user_email,
                    result["amount_to_invest"],
                    api_keys=potential_keys,
                    dry_run=False,  # Change to True for testing
                )

                if purchase_success:
                    logger.info(f"  ✓ Purchase executed successfully")
                    purchase_executed = True
                    purchase_count += 1
                    confirmation_purchase_html = make_btc_purchase_confirmation_email(
                        result["amount_to_invest"]
                    )
                    send_email(
                        subject="BTC Purchase Confirmation",
                        body=confirmation_purchase_html,
                        email_recipient=user_email,
                    )
                else:
                    logger.error(f"  ❌ Purchase execution failed")
            else:
                logger.info(f"  ℹ User not authorized for automatic purchases")

            # Send email
            email_sent = send_email_to_user(
                result["user_email"],
                result["amount_to_invest"],
                current_price=f"{result['today_price']:.2f}",
            )

            if email_sent:
                logger.info(f"  ✓ Email sent successfully to {user_email}")
                success_count += 1
                results.append(
                    {
                        "user": user_email,
                        "status": "success",
                        "amount": result["amount_to_invest"],
                        "price": result["today_price"],
                        "purchase_executed": purchase_executed,
                    }
                )
            else:
                logger.error(f"  ❌ Failed to send email to {user_email}")
                error_count += 1
                results.append(
                    {
                        "user": user_email,
                        "status": "email_failed",
                        "error": "Email sending failed",
                        "purchase_executed": purchase_executed,
                    }
                )

        except Exception as e:
            logger.error(
                f"  ❌ Unexpected error processing {user_email}: {e}", exc_info=True
            )
            error_count += 1
            results.append({"user": user_email, "status": "error", "error": str(e)})

    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"\n{'='*60}")
    logger.info(f"DAILY EMAIL JOB SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Started:  {start_time}")
    logger.info(f"Finished: {end_time}")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"")
    logger.info(f"Total users processed: {len(users)}")
    logger.info(f"✓ Successful emails:   {success_count}")
    logger.info(f"✓ Purchases executed:  {purchase_count}")
    logger.info(f"✗ Errors:              {error_count}")
    logger.info(
        f"Success rate:          {(success_count/len(users)*100):.1f}%"
        if users
        else "N/A"
    )
    logger.info(f"{'='*60}")

    # Log detailed results if there were any errors
    if error_count > 0:
        logger.info("\nDetailed Results:")
        for result in results:
            if result["status"] != "success":
                logger.info(
                    f"  ❌ {result['user']}: {result.get('error', result['status'])}"
                )


if __name__ == "__main__":
    main()
