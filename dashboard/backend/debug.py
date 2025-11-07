"""
Quick test script - run this to check your database connection.
Usage: python quick_test.py
"""

import os
import sys

# Set your environment variables here if not already set
# os.environ["SUPABASE_URL"] = "https://your-project.supabase.co"
# os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "your-service-role-key"


def quick_test():
    print("🔍 Quick Database Test\n")

    # 1. Check env vars
    print("1. Environment Variables:")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    print(f"   SUPABASE_URL: {'✓ Set' if url else '✗ Missing'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✓ Set' if key else '✗ Missing'}\n")

    if not url or not key:
        print("❌ Please set environment variables first!")
        print("\nAdd to your .env file or export:")
        print("   export SUPABASE_URL='https://xxxxx.supabase.co'")
        print("   export SUPABASE_SERVICE_ROLE_KEY='eyJxxx...'")
        return

    # 2. Initialize database
    print("2. Initializing Database:")
    try:
        from dashboard.backend.supabase_utils import initialize_database, get_database

        db = initialize_database(url, key)
        print(f"   Database initialized: {'✓' if db else '✗'}")
        print(f"   Database enabled: {'✓' if db.enabled else '✗'}")
        print(f"   Client exists: {'✓' if db.client else '✗'}\n")

        if not db.enabled:
            print("❌ Database not enabled. Check credentials.")
            return

    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        return

    # 3. Test user lookup
    print("3. Testing User Lookup:")
    test_email = "smaueltown@gmail.com"
    print(f"   Looking up: {test_email}")

    try:
        user = db.get_user_info_by_email(test_email)

        if user:
            print(f"   ✓ User found!")
            print(f"     - Email: {user.get('user_email')}")
            print(f"     - Budget: {user.get('budget')}")
            print(f"     - Start Date: {user.get('start_date')}")
            print(f"     - Investment Period: {user.get('investment_period')}")
            print(f"     - Boost Factor: {user.get('boost_factor')}")
        else:
            print(f"   ✗ User not found (returned None)")

            # Try to see all users
            print("\n   Checking table contents:")
            all_users = (
                db.client.table("users").select("user_email").limit(10).execute()
            )
            if all_users.data:
                print(f"   Found {len(all_users.data)} users:")
                for u in all_users.data:
                    print(f"     - {u.get('user_email')}")
            else:
                print(f"   ❌ Table is empty!")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n✅ Test complete!")


if __name__ == "__main__":
    quick_test()
