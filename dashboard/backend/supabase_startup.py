"""
Database configuration and initialization module.
Place this in your application startup code.
"""

import os
from typing import Optional
from dashboard.backend.supabase_utils import initialize_database, DatabaseService
import logging
import streamlit as st

logger = logging.getLogger(__name__)


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


# During application startup

db_service = setup_database()
