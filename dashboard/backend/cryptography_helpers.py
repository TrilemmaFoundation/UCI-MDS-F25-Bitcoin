import streamlit as st
import os
from cryptography.fernet import Fernet
import base64


def decrypt_value(fernet: Fernet, token_b64: str) -> str:
    """Decrypt token string back to plaintext (use in backend only)."""
    return fernet.decrypt(token_b64.encode("utf-8")).decode("utf-8")


# --- helper: get Fernet key securely from environment / streamlit secrets ---
def get_fernet():
    """
    Tries to load a Fernet key from:
      1) streamlit secrets: st.secrets["fernet_key"]
      2) env var: FERNET_KEY
    If missing, returns None and the UI will show instructions.
    """
    key = None
    # first prefer streamlit secrets
    try:
        key = st.secrets.get("fernet_key")  # recommended for deployment
    except Exception:
        key = None

    if not key:
        key = os.environ.get("FERNET_KEY")

    if key:
        # if user accidentally stored the key as str() with quotes or spaced, sanitize a bit
        key = key.strip()
        # Fernet key must be bytes
        if isinstance(key, str):
            key = key.encode("utf-8")
        return Fernet(key)
    return None


def encrypt_value(fernet: Fernet, plaintext: str) -> str:
    """Encrypt plaintext -> base64 string safe to store in DB."""
    token = fernet.encrypt(plaintext.encode("utf-8"))
    # token is already base64 urlsafe bytes; return as utf-8 string
    return token.decode("utf-8")
