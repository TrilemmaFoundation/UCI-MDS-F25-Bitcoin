# dashboard/email_helpers/coinbase_purchase_helper.py
import os
import logging
from typing import Optional, Dict, Any
import json
import uuid
from datetime import datetime

from coinbase.rest import RESTClient

logger = logging.getLogger(__name__)

# Coinbase API configuration
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY", "")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET", "")

test_me = {"client": COINBASE_API_KEY, "secret": COINBASE_API_SECRET}

# User whitelist - only this email can execute transactions
AUTHORIZED_EMAIL = "smaueltown@gmail.com"


def get_coinbase_client(api_keys: dict) -> Optional[RESTClient]:
    """
    Initialize and return a Coinbase REST client.

    Returns:
        RESTClient instance or None if credentials are missing
    """
    # if not COINBASE_API_KEY or not COINBASE_API_SECRET:
    #     logger.error("Coinbase API credentials not configured")
    #     return None

    try:
        client = RESTClient(api_key=api_keys["client"], api_secret=api_keys["secret"])
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Coinbase client: {e}", exc_info=True)
        return None


def test_connection(api_keys: dict) -> bool:
    """
    Test the Coinbase API connection.

    Returns:
        True if connection is successful, False otherwise
    """
    client = get_coinbase_client(api_keys)
    if not client:
        return False

    try:
        # Try to get accounts to verify connection
        accounts = client.get_accounts()
        logger.info("✓ Successfully connected to Coinbase API")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Coinbase API: {e}", exc_info=True)
        return False


def get_btc_account_info(api_keys: dict) -> Optional[Dict[str, Any]]:
    """
    Get BTC account information.

    Returns:
        Dictionary with account info or None if not found
    """
    client = get_coinbase_client(api_keys)
    if not client:
        return None

    try:
        accounts = client.get_accounts()

        for account in accounts["accounts"]:
            if account["currency"] == "BTC":
                logger.info("Found BTC account")
                return account

        logger.warning("No BTC account found")
        return None

    except Exception as e:
        logger.error(f"Error getting BTC account: {e}", exc_info=True)
        return None


def execute_btc_purchase(
    user_email: str, amount_usd: float, api_keys: dict, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute a Bitcoin purchase on Coinbase for authorized user only.

    Args:
        user_email: Email of the user making the purchase
        amount_usd: Dollar amount to spend on BTC
        dry_run: If True, validate but don't execute the purchase

    Returns:
        Dictionary with transaction details or error information
    """
    result = {
        "success": False,
        "user_email": user_email,
        "amount_usd": amount_usd,
        "dry_run": dry_run,
        "message": "",
        "order_id": None,
        "client_order_id": None,
        "btc_amount": None,
        "filled_value": None,
        "error": None,
    }

    # Check if API credentials are configured
    if not api_keys:
        result["error"] = "Coinbase API credentials not configured"
        logger.error(result["error"])
        return result

    # SECURITY: Only allow authorized user
    # if user_email != AUTHORIZED_EMAIL:
    #     result["error"] = f"User {user_email} is not authorized for automatic purchases"
    #     logger.warning(result["error"])
    #     return result

    # Validate amount
    if amount_usd <= 0:
        result["error"] = f"Invalid purchase amount: ${amount_usd}"
        logger.error(result["error"])
        return result

    # Minimum purchase check (Coinbase typically requires $1 minimum)
    if amount_usd < 1.0:
        result["error"] = (
            f"Amount ${amount_usd:.2f} is below minimum purchase threshold"
        )
        logger.warning(result["error"])
        return result

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Initiating BTC purchase for {user_email}: ${amount_usd:.2f}"
    )

    try:
        # Initialize client
        client = get_coinbase_client(api_keys)
        if not client:
            result["error"] = "Failed to initialize Coinbase client"
            return result

        # Verify BTC account exists
        btc_account = get_btc_account_info(api_keys)
        if not btc_account:
            result["error"] = "Could not find BTC account"
            return result

        if dry_run:
            result["success"] = True
            result["message"] = (
                f"Dry run successful. Would purchase ${amount_usd:.2f} of BTC"
            )
            logger.info(result["message"])
            return result

        # Generate unique client order ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        client_order_id = f"btc-dca-{timestamp}-{uuid.uuid4().hex[:8]}"

        logger.info(f"  Client Order ID: {client_order_id}")
        logger.info(f"  Product: BTC-USD")
        logger.info(f"  Quote Size: ${amount_usd:.2f} USD")

        # Execute the market buy order
        order = client.market_order_buy(
            client_order_id=client_order_id,
            product_id="BTC-USD",
            quote_size=f"{amount_usd:.2f}",
        )

        # Convert order to dictionary
        order_dict = order.to_dict()

        # Extract order details
        order_id = order_dict.get("order_id") or order_dict.get(
            "success_response", {}
        ).get("order_id")
        success = order_dict.get("success", False)

        if success or order_id:
            result["success"] = True
            result["order_id"] = order_id
            result["client_order_id"] = client_order_id

            # Try to extract filled amounts
            success_response = order_dict.get("success_response", {})
            result["filled_value"] = (
                success_response.get("order_configuration", {})
                .get("market_market_ioc", {})
                .get("quote_size")
            )

            result["message"] = (
                f"Successfully placed BTC buy order for ${amount_usd:.2f}"
            )

            logger.info(f"✓ {result['message']}")
            logger.info(f"  Order ID: {result['order_id']}")
            # logger.info(f"  Full response: {json.dumps(order_dict, indent=2)}")

        else:
            result["error"] = (
                f"Order placement failed: {json.dumps(order_dict, indent=2)}"
            )
            logger.error(result["error"])

        return result

    except Exception as e:
        result["error"] = f"Error during purchase: {str(e)}"
        logger.error(result["error"], exc_info=True)
        return result


def execute_purchase_for_user(
    user_email: str,
    amount_to_invest: float,
    api_keys: dict,
    dry_run: bool = False,
) -> bool:
    """
    Wrapper function to execute purchase and return simple success/failure.
    This function is designed to be called from the daily emailer.

    Args:
        user_email: User's email address
        amount_to_invest: Dollar amount to invest
        dry_run: If True, simulate the purchase without executing

    Returns:
        True if purchase succeeded, False otherwise
    """
    # print(user_email, amount_to_invest, api_keys, dry_run)
    result = execute_btc_purchase(user_email, amount_to_invest, api_keys, dry_run)

    if result["success"]:
        logger.info(f"Purchase completed for {user_email}: {result['message']}")
        return True
    else:
        logger.error(
            f"Purchase failed for {user_email}: {result.get('error', 'Unknown error')}"
        )
        return False


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("\n" + "=" * 60)
    print("Testing Coinbase Purchase Helper")
    print("=" * 60)

    # Check credentials first
    print("\n[DIAGNOSTICS]")
    print(f"API Key present: {'Yes' if COINBASE_API_KEY else 'No'}")
    print(f"API Key length: {len(COINBASE_API_KEY) if COINBASE_API_KEY else 0}")
    print(f"API Secret present: {'Yes' if COINBASE_API_SECRET else 'No'}")
    print(
        f"API Secret length: {len(COINBASE_API_SECRET) if COINBASE_API_SECRET else 0}"
    )

    if not COINBASE_API_KEY or not COINBASE_API_SECRET:
        print("\n❌ ERROR: Missing API credentials!")
        print("Please set environment variables:")
        print("  export COINBASE_API_KEY='your_key'")
        print("  export COINBASE_API_SECRET='your_secret'")
        exit(1)

    # Test connection
    print("\n[CONNECTION TEST]")
    if test_connection(test_me):
        print("✓ API connection successful")
    else:
        print("✗ API connection failed")
        exit(1)

    # Get BTC account info
    print("\n[ACCOUNT INFO]")
    btc_account = get_btc_account_info(test_me)
    if btc_account:
        print(f"✓ BTC Account found")

    test_email = AUTHORIZED_EMAIL
    test_amount = 1.0

    print("\n[TEST SCENARIOS]")
    print(f"\nTest 1: Dry run purchase")
    result = execute_btc_purchase(
        test_email, test_amount, api_keys=test_me, dry_run=False
    )
    print(f"Result: {result}")

    # print(f"\nTest 2: Unauthorized user")
    # result = execute_btc_purchase("unauthorized@example.com", test_amount, dry_run=True)
    # print(f"Result: {result}")

    # print(f"\nTest 3: Invalid amount")
    # result = execute_btc_purchase(test_email, -5.0, dry_run=True)
    # print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("Note: Set dry_run=False to execute real purchases")
    print("=" * 60)
