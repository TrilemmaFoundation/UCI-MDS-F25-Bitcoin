import os
import streamlit as st
from cryptography.fernet import Fernet
import time

# your backend helpers (assumed to accept encrypted strings)
from dashboard.backend.supabase_utils import (
    initialize_database,
    add_coinbase_info,
    get_full_user_info,
    remove_user_api_keys,
)
from dashboard.backend.cryptography_helpers import get_fernet, encrypt_value

# initialize DB (if needed)
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
db = initialize_database(url, key)


# ---------- UI ----------
st.set_page_config(
    page_title="Coinbase API Settings", page_icon="🔐", layout="centered"
)

# Small CSS for a cleaner, more professional card-like layout.
st.markdown(
    """
    <style>
    .card {
        background: #ffffff;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 6px 18px rgba(21, 32, 43, 0.08);
        max-width: 800px;
        margin: 12px auto;
    }
    .small-muted { color: #6b7280; font-size: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# st.markdown('<div class="card">', unsafe_allow_html=True)

st.title("Coinbase auto accumulation")

# Get user email from Streamlit's user object (your original approach)
user_email = None
try:
    # keep your existing approach but guard against missing attributes
    user_email = st.user.get("email") if hasattr(st, "user") else None
except Exception:
    # fallback if st.user is not available in your environment
    user_email = os.environ.get("TEST_USER_EMAIL")  # optional test/dev hook

if not user_email:
    st.warning(
        "Please login using the sidebar to opt in to automatic bitcoin accumulation."
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

potential_already_coinbased = get_full_user_info(user_email=user_email)

if (
    "coinbase_client_api_key" in potential_already_coinbased.keys()
    and "coinbase_secret_api_key" in potential_already_coinbased.keys()
    and potential_already_coinbased["coinbase_client_api_key"]
    and potential_already_coinbased["coinbase_secret_api_key"]
    and user_email
):
    st.write(
        "You've successfully integrated your Coinbase account with our daily accumulator! To unsubscribe, click or press the button below."
    )
    unsubscribe = st.button("Unsubscribe")
    if unsubscribe:
        remove_user_api_keys(user_email=user_email)
        st.success(
            "We've deleted your api keys from our database. You can re-enter them any time you'd like!"
        )
        time.sleep(3)
        st.rerun()


else:
    st.write(
        "Add your Coinbase API credentials below. We encrypt them **before** storing them in the database."
    )
    st.caption(
        "We recommend using a dedicated API key with only the permissions required for buys/transfers."
    )

    # show an info row and a small notice about funding requirement
    st.info(
        "We encrypt your API keys before storing them. Only store keys you are comfortable sharing with this service."
    )
    st.error(
        "NOTE: This will only execute daily IF you have enough funds in your Coinbase account and the key has appropriate permissions."
    )

    fernet = get_fernet()
    if fernet is None:
        st.warning(
            "Encryption key is not configured. For security you must set a Fernet key in `st.secrets['fernet_key']` or in the environment variable `FERNET_KEY`."
        )
        with st.expander("How to generate and store a Fernet key (one-time):"):
            st.code(
                """# generate a key locally (do NOT put into source control)
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())  # copy this into st.secrets or FERNET_KEY"""
            )
            st.write(
                "In Streamlit Cloud: add a secret named `fernet_key` with the generated value. "
                "In other deployments: set environment variable `FERNET_KEY` to that value."
            )

    # Form for better UX and atomic submit
    with st.form(key="coinbase_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            client_key = st.text_input(
                "Coinbase Client API Key",
                placeholder="xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx",
                help="Enter your Coinbase API key.",
            )
        with col2:
            st.write("")  # align vertical position
            st.write("")
            st.write("")
            # show lock icon and label for clarity
            st.markdown("🔒 **Encrypted**")

        secret_key = st.text_input(
            "Coinbase Secret API Key",
            type="password",
            placeholder="-----BEGIN EC PRIVATE KEY-----...-----END EC PRIVATE KEY-----",
            help="Secret API key (hidden).",
        )
        submitted = st.form_submit_button(label="Save Coinbase Credentials")

    if submitted:
        if not client_key or not secret_key:
            st.error("Please provide both the client API key and secret API key.")
        elif fernet is None:
            st.error(
                "Encryption is not configured. Cannot store API keys until a Fernet key is set."
            )
        else:
            # encrypt before sending to backend
            try:
                # print(user_email)
                enc_client = encrypt_value(fernet, client_key)
                enc_secret = encrypt_value(fernet, secret_key)
                # print(len(enc_client), len(enc_secret))
                # call your backend - store encrypted values
                success = add_coinbase_info(
                    user_email=user_email,
                    api_client_key=enc_client,
                    api_secret_key=enc_secret,
                )
                if success:
                    # st.rerun()
                    st.success(
                        "Coinbase credentials saved and encrypted successfully. Now, when you get your daily email, we will attempt to run the bitcoin accumulation transaction."
                    )
                    time.sleep(3)
                    st.rerun()

                else:
                    st.error(
                        "Oops, we weren't able to add your info. Please try again later!"
                    )
                    print("did not work")

            except Exception as e:
                print(e)
                st.exception(f"Failed to encrypt/save keys: {e}")

    # Helpful debugging / admin area (collapsed)
    # with st.expander("Advanced / Admin (DO NOT share)"):
    #     st.write(
    #         "If you need to decrypt a stored token on the server, use the server-side `decrypt_value` function with the same Fernet key."
    #     )
    #     st.markdown("**Local debug email:** " + user_email)
    # st.markdown("</div>", unsafe_allow_html=True)
