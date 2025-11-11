"""
Production-ready Supabase/PostgreSQL database service.
Replaces Google Sheets backend with proper database operations.
"""

import streamlit as st
import os
from supabase import create_client, Client
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for managing user data in Supabase/PostgreSQL."""

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize the database service.

        Args:
            supabase_url: Your Supabase project URL
            supabase_key: Your Supabase API key (service_role for backend)
        """
        self.enabled = bool(supabase_url and supabase_key)

        if self.enabled:
            try:
                self.client: Client = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
                self.client = None
        else:
            self.client = None
            logger.warning(
                "Supabase credentials not provided, database operations disabled"
            )

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Centralized error handling and logging."""
        logger.error(f"Error during {operation}: {str(error)}", exc_info=True)

    def add_user_info(self, user_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add a new user to the database.

        Args:
            user_info: Dictionary containing user information with keys:
                - user_email (str): User's email address
                - budget (str/float): Investment budget
                - start_date (str): Start date in YYYY-MM-DD format
                - investment_period (str/int): Investment period in months
                - boost_factor (str/float): Boost factor multiplier
                - email_opted_in (bool): Email opt-in status

        Returns:
            Dictionary with inserted user data or None if failed
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, skipping user info save")
            return None

        # Validate required fields
        required_fields = [
            "user_email",
            "budget",
            "start_date",
            "investment_period",
            "boost_factor",
            "email_opted_in",
        ]

        missing_fields = [field for field in required_fields if field not in user_info]
        if missing_fields:
            logger.error(f"Missing required fields: {', '.join(missing_fields)}")
            return None

        try:
            # Prepare data for insertion
            data = {
                "user_email": user_info["user_email"],
                "budget": float(user_info["budget"]),
                "start_date": user_info["start_date"],
                "investment_period": int(user_info["investment_period"]),
                "boost_factor": float(user_info["boost_factor"]),
                "email_opted_in": bool(user_info["email_opted_in"]),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = self.client.table("users").insert(data).execute()

            if response.data:
                logger.info(f"Successfully added user: {user_info['user_email']}")
                return response.data[0]
            else:
                logger.error(f"Failed to add user, no data returned")
                return None

        except Exception as e:
            self._handle_error("add_user_info", e)
            return None

    def get_user_info_by_email(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information by email address.

        Args:
            user_email: Email address to search for

        Returns:
            Dictionary containing user information or None if not found
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, returning default values")
            return {
                "user_email": user_email,
                "budget": "1000",
                "start_date": "2024-10-18",
                "investment_period": "12",
                "boost_factor": "1.25",
            }

        try:
            response = (
                self.client.table("users")
                .select("*")
                .eq("user_email", user_email)
                .maybe_single()
                .execute()
            )

            if response.data:
                # Convert to match original format
                return {
                    "user_email": response.data["user_email"],
                    "budget": str(response.data["budget"]),
                    "start_date": response.data["start_date"],
                    "investment_period": str(response.data["investment_period"]),
                    "boost_factor": str(response.data["boost_factor"]),
                }
            else:
                logger.info(f"No user found with email: {user_email}")
                return None

        except Exception as e:
            self._handle_error("get_user_info_by_email", e)
            return None

    def get_full_user_info(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information by email address.

        Args:
            user_email: Email address to search for

        Returns:
            Dictionary containing user information or None if not found
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, returning default values")
            return {
                "user_email": user_email,
                "budget": "1000",
                "start_date": "2024-10-18",
                "investment_period": "12",
                "boost_factor": "1.25",
            }

        try:
            response = (
                self.client.table("users")
                .select("*")
                .eq("user_email", user_email)
                .maybe_single()
                .execute()
            )

            if response.data:
                return response.data
            else:
                logger.info(f"No user found with email: {user_email}")
                return None

        except Exception as e:
            self._handle_error("get_user_info_by_email", e)
            return None

    def update_user_preferences(self, user_info: Dict[str, Any]) -> bool:
        """
        Update user preferences in the database.

        Args:
            user_info: Dictionary with user_email (required) and any fields to update

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, skipping preference update")
            return False

        if "user_email" not in user_info:
            logger.error("user_email is required for updating preferences")
            return False

        user_email = user_info["user_email"]

        try:
            # Remove user_email from update data and prepare update dict
            update_data = {k: v for k, v in user_info.items() if k != "user_email"}

            # Convert numeric fields if present
            if "budget" in update_data:
                update_data["budget"] = float(update_data["budget"])
            if "investment_period" in update_data:
                update_data["investment_period"] = int(update_data["investment_period"])
            if "boost_factor" in update_data:
                update_data["boost_factor"] = float(update_data["boost_factor"])

            # Always update the updated_at timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()

            response = (
                self.client.table("users")
                .update(update_data)
                .eq("user_email", user_email)
                .execute()
            )

            if response.data:
                logger.info(f"Successfully updated user: {user_email}")
                return True
            else:
                logger.warning(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("update_user_preferences", e)
            return False

    def does_user_exist(self, user_email: str) -> bool:
        """
        Check if a user exists in the database.

        Args:
            user_email: Email address to check

        Returns:
            True if user exists, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            response = (
                self.client.table("users")
                .select("user_email", count="exact")
                .eq("user_email", user_email)
                .execute()
            )

            return response.count > 0 if response.count is not None else False

        except Exception as e:
            self._handle_error("does_user_exist", e)
            return False

    def add_user_to_email_list(self, user_email: str) -> bool:
        """
        Opt user into email list.

        Args:
            user_email: Email address of user to opt in

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, skipping email list update")
            return False

        try:
            response = (
                self.client.table("users")
                .update(
                    {
                        "email_opted_in": True,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
                .eq("user_email", user_email)
                .execute()
            )

            if response.data:
                logger.info(f"Added user to email list: {user_email}")
                return True
            else:
                logger.warning(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("add_user_to_email_list", e)
            return False

    def add_coinbase_info(
        self, user_email: str, client_api_key: str, secret_api_key: str
    ) -> bool:
        """
        Opt user into automated coinbase transactions.

        Args:
            user_email: which user we want to opt in
            client_api_key: coinbase client api key
            secret_api_key: coinbase secret api key

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            print("db not configured")
            logger.warning("Database not configured, skipping email list update")
            return False

        try:
            response = (
                self.client.table("users")
                .update(
                    {
                        "coinbase_client_api_key": client_api_key,
                        "coinbase_secret_api_key": secret_api_key,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
                .eq("user_email", user_email)
                .execute()
            )

            if response.data:
                logger.info(f"Added api keys to db for user: {user_email}")
                return True
            else:
                logger.warning(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("add_user_to_email_list", e)
            return False

    def is_user_on_email_list(self, user_email: str) -> bool:
        """
        Check if user is opted into email list.

        Args:
            user_email: Email address to check

        Returns:
            True if user is opted in, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured")
            return False

        try:
            response = (
                self.client.table("users")
                .select("email_opted_in")
                .eq("user_email", user_email)
                .maybe_single()
                .execute()
            )

            if response.data:
                return bool(response.data.get("email_opted_in", False))
            else:
                logger.info(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("is_user_on_email_list", e)
            return False

    def is_user_coinbased(self, user_email: str) -> bool:
        """
        Check if user is opted into coinbase list.

        Args:
            user_email: Email address to check

        Returns:
            True if user is opted in, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured")
            return False

        try:
            response = (
                self.client.table("users")
                .select("coinbase_client_api_key")
                .eq("user_email", user_email)
                .maybe_single()
                .execute()
            )

            if response.data:
                return bool(response.data.get("coinbase_client_api_key", False))
            else:
                logger.info(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("is_user_on_email_list", e)
            return False

    def remove_user_from_email_list(self, user_email: str) -> bool:
        """
        Opt user out of email list.

        Args:
            user_email: Email address of user to opt out

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, skipping email list update")
            return False

        try:
            response = (
                self.client.table("users")
                .update(
                    {
                        "email_opted_in": False,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
                .eq("user_email", user_email)
                .execute()
            )

            if response.data:
                logger.info(f"Removed user from email list: {user_email}")
                return True
            else:
                logger.warning(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("remove_user_from_email_list", e)
            return False

    def remove_user_api_keys(self, user_email: str) -> bool:
        """
        Opt user out of auto btc accumulation

        Args:
            user_email: Email address of user to opt out

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured, skipping email list update")
            return False

        try:
            response = (
                self.client.table("users")
                .update(
                    {
                        "coinbase_client_api_key": None,
                        "coinbase_secret_api_key": None,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )
                .eq("user_email", user_email)
                .execute()
            )

            if response.data:
                logger.info(f"Removed user's api keys': {user_email}")
                return True
            else:
                logger.warning(f"User not found: {user_email}")
                return False

        except Exception as e:
            self._handle_error("remove_user_from_email_list", e)
            return False

    def get_all_email_subscribers(self) -> list[Dict[str, Any]]:
        """
        Get all users who are opted into the email list.

        Returns:
            List of user dictionaries
        """
        if not self.enabled or not self.client:
            logger.warning("Database not configured")
            return []

        try:
            response = (
                self.client.table("users")
                .select("*")
                .eq("email_opted_in", True)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            self._handle_error("get_all_email_subscribers", e)
            return []


# Singleton pattern for easy import
_db_service_instance: Optional[DatabaseService] = None


def initialize_database(supabase_url: str, supabase_key: str) -> DatabaseService:
    """
    Initialize the database service singleton.

    Args:
        supabase_url: Your Supabase project URL
        supabase_key: Your Supabase API key

    Returns:
        Initialized DatabaseService instance
    """
    global _db_service_instance
    _db_service_instance = DatabaseService(supabase_url, supabase_key)
    return _db_service_instance


def get_database() -> Optional[DatabaseService]:
    """
    Get the database service instance.

    Returns:
        DatabaseService instance or None if not initialized
    """
    return _db_service_instance


def get_supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    """
    Retrieve Supabase credentials from environment variables.

    Returns:
        Tuple of (supabase_url, supabase_key)
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )  # Use service_role for backend

    if not supabase_url:
        logger.warning("SUPABASE_URL environment variable not set")
    if not supabase_key:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY environment variable not set")

    return supabase_url, supabase_key


@st.cache_resource
def setup_database() -> DatabaseService:
    """
    Initialize the database service with credentials from environment.
    Call this during application startup.

    Returns:
        Initialized DatabaseService instance
    """
    supabase_url, supabase_key = get_supabase_credentials()

    db_service = initialize_database(supabase_url, supabase_key)

    if db_service.enabled:
        logger.info("Database service initialized successfully")
    else:
        logger.warning("Database service disabled - credentials not provided")

    return db_service


# Convenience functions that mirror the original API
def add_user_info_to_sheet(user_info: dict) -> Optional[Dict[str, Any]]:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.add_user_info(user_info) if db else None


def get_user_info_by_email(user_email: str) -> Optional[Dict[str, Any]]:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.get_user_info_by_email(user_email) if db else None


def get_full_user_info(user_email: str) -> Optional[Dict[str, Any]]:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.get_full_user_info(user_email) if db else None


def update_user_preferences(new_user_info: dict) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.update_user_preferences(new_user_info) if db else False


def does_user_exist(user_email: str) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.does_user_exist(user_email) if db else False


def add_user_to_email_list(user_email: str) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.add_user_to_email_list(user_email) if db else False


def add_coinbase_info(
    user_email: str, api_client_key: str, api_secret_key: str
) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    print(db)
    return (
        db.add_coinbase_info(
            user_email=user_email,
            client_api_key=api_client_key,
            secret_api_key=api_secret_key,
        )
        if db
        else False
    )


def is_user_already_on_email(user_email: str) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.is_user_on_email_list(user_email) if db else False


def is_user_coinbased(user_email: str) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.is_user_coinbased(user_email) if db else False


def remove_user_from_email_list(user_email: str) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.remove_user_from_email_list(user_email) if db else False


def remove_user_api_keys(user_email: str) -> bool:
    """Legacy function name for backwards compatibility."""
    db = get_database()
    return db.remove_user_api_keys(user_email) if db else False
