import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dashboard.config import (
    GOOGLE_SHEETS_PRIVATE_KEY,
    GOOGLE_SHEETS_PRIVATE_KEY_ID,
    GOOGLE_SHEETS_CLIENT_ID,
)
from datetime import date, timedelta

private_key = GOOGLE_SHEETS_PRIVATE_KEY.replace("\\n", "\n")
private_key_id = GOOGLE_SHEETS_PRIVATE_KEY_ID
client_id = GOOGLE_SHEETS_CLIENT_ID
# Define the scope of the API access
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

cred = {
    "type": "service_account",
    "project_id": "cs-autotranslation",
    "private_key_id": private_key_id,
    "private_key": private_key,
    "client_email": "523461412539-compute@developer.gserviceaccount.com",
    "client_id": client_id,
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/523461412539-compute%40developer.gserviceaccount.com",
    "universe_domain": "googleapis.com",
}
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred, scope)
client = gspread.authorize(creds)

sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1xOPm_uRawGakD0bc77i_1QoSxwi9Jf3hXz9_822iHP0/edit?gid=0#gid=0"
)
worksheet = sheet.get_worksheet(0)


def first_blank_row():
    """
    Return the row index (1-based) of the first blank row (i.e. the next empty after the last non-empty one).
    """
    # Get all values in the sheet as a list of lists (rows)
    rows = worksheet.get_all_values()
    # rows is a list of lists; each inner list is a row (possibly shorter if trailing blanks)
    # The number of “used” rows is len(rows). So first blank row is len(rows) + 1.
    return len(rows) + 1


def add_user_info_to_sheet(user_info: dict):

    # validate input dict
    validation_fields = [
        "user_email",
        "budget",
        "start_date",
        "investment_period",
        "boost_factor",
    ]

    for field in validation_fields:
        if field not in user_info.keys():
            print(
                f"did not get enough fields to populate spreadsheet. please add the {field} field"
            )
            return None

    # format data for input
    master_list = [
        user_info["user_email"],
        user_info["budget"],
        user_info["start_date"],
        user_info["investment_period"],
        user_info["boost_factor"],
    ]

    worksheet.insert_row(master_list, first_blank_row())

    print("row added successfully!")


sample_in = {
    "user_email": "smaueltown@gmail.com",
    "budget": "1",
    "start_date": "2025-10-16",
    "investment_period": "12",
    "boost_factor": "1.25",
}
# add_user_info_to_sheet(sample_in)


def get_user_info_by_email(user_email: str):
    """
    Find a user by email and return all values from their row.

    Args:
        user_email: The email address to search for

    Returns:
        list: All cell values from the matching row, or None if not found
    """
    try:
        # Find the cell containing the email
        cell = worksheet.find(user_email)

        if cell:
            # Get all values from that row
            row_values = worksheet.row_values(cell.row)
            to_return = {
                "user_email": row_values[0],
                "budget": row_values[1],
                "start_date": row_values[2],
                "investment_period": row_values[3],
                "boost_factor": row_values[4],
            }
            return to_return
        else:
            print(f"No user found with email: {user_email}")
            return None

    except Exception as e:
        print(f"Error searching for user: {e}")
        return None


# Usage
# user_info = get_user_info_by_email("smaueltown@gmail.com")
# if user_info:
#     print(user_info)


def update_user_preferences(new_user_info: dict):
    try:
        # Find the cell containing the email
        cell = worksheet.find(new_user_info["user_email"])

        if cell:
            row_num = cell.row
            print(f"Found user at row {row_num}")

            # Get headers to map column positions
            headers = worksheet.row_values(1)

            # Update each field in new_user_info
            for field, value in new_user_info.items():
                if field in headers:
                    col_num = headers.index(field) + 1  # +1 for 1-based indexing
                    worksheet.update_cell(row_num, col_num, value)

            print(f"Updated user: {new_user_info['user_email']}")
        else:
            print(f"User not found: {new_user_info['user_email']}")

    except Exception as e:
        print("error:", e)


# Example usage
sample_in = {
    "user_email": "smaueltown@gmail.com",
    "budget": 5000,
    "start_date": "2025-01-01",
    "investment_period": 12,
    "boost_factor": 1.5,
}

# update_user_preferences(sample_in)


def does_user_exist(user_email: str):
    try:
        # Find the cell containing the email
        cell = worksheet.find(user_email)

        if cell:
            return True
        else:
            return False
    except Exception as e:
        return False


# print(does_user_exist("smaueltown@gmail.com"))
