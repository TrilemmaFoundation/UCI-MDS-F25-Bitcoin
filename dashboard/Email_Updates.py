import streamlit as st
from dashboard.email_helpers.email_utils import send_email
from dashboard.email_helpers.welcome_email import welcome_email

# from dashboard.backend.gsheet_utils import (
#     is_user_already_on_email,
#     add_user_to_email_list,
#     remove_user_from_email_list,
# )
from dashboard.backend.supabase_utils import (
    is_user_already_on_email,
    add_user_to_email_list,
    remove_user_from_email_list,
)
import time

# Page configuration
st.set_page_config(
    page_title="Email Preferences",
    page_icon="📧",
    layout="centered",
    initial_sidebar_state="auto",
)

# Custom CSS for modern, professional styling
st.markdown(
    """
    <style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 0;
    }
    /* Card container */
    .card {
        background-color: #161B22;
        border-radius: 16px;
        padding: 3rem 2.5rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        margin: 2rem auto;
        max-width: 600px;
        animation: slideUp 0.5s ease-out;
    }
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    /* Success card */
    .success-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 16px;
        padding: 3rem 2.5rem;
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
        margin: 2rem auto;
        max-width: 600px;
        text-align: center;
        animation: slideUp 0.5s ease-out;
    }
    /* Icons */
    .icon {
        font-size: 4rem;
        display: block;
    }
    /* Headers */
    h1 {
        color: #1a202c;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .success-card h1 {
        color: white;
    }
    /* Subheaders */
    .subtitle {
        color: #F7931A;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    
    .success-card .subtitle {
        color: rgba(255, 255, 255, 0.9);
    }
    /* Feature list */
    .feature-list {
        background: #f7fafc;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 2rem 0;
    }
    .feature-item {
        display: flex;
        align-items: center;
        padding: 0.75rem 0;
        color: #2d3748;
    }
    .feature-icon {
        color: #667eea;
        margin-right: 1rem;
        font-size: 1.3rem;
    }
    /* Buttons */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.875rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    .stButton > button:active {
        transform: translateY(0);
    }transform: translateY(0);
    }
    /* Login prompt styling */
    .login-prompt {
        background: white;
        border-radius: 16px;
        padding: 3rem 2.5rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        text-align: center;
        animation: slideUp 0.5s ease-out;
    }
    .login-icon {
        font-size: 4rem;
        color: #667eea;
        margin-bottom: 1.5rem;
    }
    /* Info box */
    .info-box {
        background: #ebf4ff;
        border-left: 4px solid #667eea;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 1.5rem 0;
        color: #2c5282;
    }
    /* Badge */
    .badge {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    /* Spinner overlay */
    .spinner-overlay {
        text-align: center;
        padding: 2rem;
    }
    /* Checkmark animation */
    @keyframes checkmark {
        0% {
            stroke-dashoffset: 100px;
        }
        100% {
            stroke-dashoffset: 0;
        }
    }
    .checkmark {
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
    }
    .checkmark-circle {
        stroke-dasharray: 166;
        stroke-dashoffset: 166;
        stroke-width: 3;
        stroke: #48bb78;
        fill: none;
        animation: checkmark 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
    }
    .checkmark-check {
        transform-origin: 50% 50%;
        stroke-dasharray: 48;
        stroke-dashoffset: 48;
        stroke: #48bb78;
        stroke-width: 3;
        fill: none;
        animation: checkmark 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.5s forwards;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "subscription_confirmed" not in st.session_state:
    st.session_state.subscription_confirmed = False
if "processing" not in st.session_state:
    st.session_state.processing = False

# Get user info
potential_email = st.user.get("email")
user_name = st.user.get("name", "there")
logged_in = potential_email is not None


# Main application logic
def render_already_subscribed():
    """Render the UI for users already subscribed"""
    html_content = f"""
        <div class="success-card">
            <span class="icon">✅</span>
            <h1>You're All Set, {user_name.split(' ')[0]}!</h1>
            <p class="subtitle">
                You're already subscribed to our daily email updates. 
                We'll keep you informed with the latest insights delivered straight to your inbox.
            </p>
            <div class="info-box" style="background: rgba(255, 255, 255, 0.2); border-left: 4px solid white; color: white;">
                📧 Email: <strong>{potential_email}</strong>
            </div>
        </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

    # Action buttons in columns
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.switch_page("dashboard/Daily_Schedule.py")
    with col2:
        # Initialize session state for confirmation
        if "show_unsub_confirm" not in st.session_state:
            st.session_state.show_unsub_confirm = False

        if not st.session_state.show_unsub_confirm:
            if st.button("❌ Unsubscribe", use_container_width=True):
                st.session_state.show_unsub_confirm = True
                st.rerun()
        else:
            st.warning("Are you sure?")
            col_yes, col_no = st.columns([2, 1])
            with col_yes:
                if st.button("Yes, Unsubscribe", use_container_width=True):
                    print(f"removing {potential_email}")
                    remove_user_from_email_list(user_email=potential_email)
                    st.session_state.show_unsub_confirm = False
                    st.toast("Sorry to see you go! You can always subscribe again.")
                    time.sleep(1)
                    st.rerun()
            with col_no:
                if st.button("❌", use_container_width=True):
                    st.session_state.show_unsub_confirm = False
                    st.rerun()


def render_subscription_form():
    """Render the subscription form for new users"""
    html_content = f"""
        <div class="card">
            <div style="text-align: center;">
                <span class="badge">DAILY UPDATES</span>
            </div>
            <span class="icon" style="text-align: center;">📧</span>
            <h1>Stay in the Loop</h1>
            <p class="subtitle">
                Get daily insights and updates delivered straight to your inbox. 
                Join our community and never miss an important update.
            </p>
            <div class="feature-list">
                <div class="feature-item">
                    <span class="feature-icon">✨</span>
                    <span>Daily curated content and insights</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🎯</span>
                    <span>Unsubscribe anytime, no questions asked</span>
                </div>
            </div>
            <div class="info-box">
                <strong>Your email:</strong> {potential_email}
            </div>
        </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

    # Subscription button
    if st.session_state.processing:
        st.markdown(
            """
            <div class="spinner-overlay">
                <p style="color: #667eea; font-size: 1.1rem;">
                    🔄 Setting up your subscription...
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Subscribe to Daily Updates", use_container_width=True):
                st.session_state.processing = True
                st.rerun()


def process_subscription():
    """Process the subscription and show confirmation"""
    try:
        # Update user email preference
        add_user_to_email_list(potential_email)

        # Send welcome email
        send_email(
            email_recipient=potential_email,
            subject="Welcome to Daily Updates!",
            body=welcome_email(user_name),
        )

        st.session_state.subscription_confirmed = True
        st.session_state.processing = False

    except Exception as e:
        st.session_state.processing = False
        st.error(f"❌ Oops! Something went wrong: {str(e)}")
        st.info("💡 Please try again or contact support if the issue persists.")


def render_subscription_success():
    """Render success confirmation"""
    html_content = f"""
        <div class="success-card">
            <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
                <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
            </svg>
            <h1>Welcome Aboard! 🎉</h1>
            <p class="subtitle">
                You've successfully subscribed to daily email updates. 
                Check your inbox at <strong>{potential_email}</strong> for a welcome message!
            </p>
            <div class="info-box" style="background: rgba(255, 255, 255, 0.2); border-left: 4px solid white; color: white;">
                📬 You'll receive your first update within 24 hours
            </div>
        </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

    # Navigation button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🏠 Go to Dashboard", use_container_width=True):
            st.session_state.subscription_confirmed = False
            st.switch_page("dashboard/Daily_Schedule.py")


def render_login_prompt():
    """Render login prompt for non-authenticated users"""
    html_content = """
        <div class="login-prompt">
            <div class="login-icon">🔐</div>
            <h1>Authentication Required</h1>
            <p class="subtitle">
                To subscribe to daily email updates, please log in using 
                the button in the sidebar. We'll keep your information secure 
                and only use it to send you valuable updates.
            </p>
            <div class="feature-list" style="max-width: 400px; margin: 2rem auto;">
                <div class="feature-item">
                    <span class="feature-icon">🔒</span>
                    <span>Secure authentication</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🛡️</span>
                    <span>Privacy protected</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⚡</span>
                    <span>Quick setup</span>
                </div>
            </div>
        </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)


# Main rendering logic
if not logged_in:
    # User not logged in
    render_login_prompt()

elif st.session_state.subscription_confirmed:
    # Show success message
    render_subscription_success()

elif st.session_state.processing:
    # Process subscription
    render_subscription_form()
    process_subscription()
    st.rerun()

elif is_user_already_on_email(potential_email):
    # User already subscribed
    render_already_subscribed()

else:
    # New user - show subscription form
    render_subscription_form()
