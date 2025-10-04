# ui/app/main.py
import streamlit as st
import os
from streamlit_oauth import OAuth2Component
from dotenv import load_dotenv
import jwt

# Load environment variables from .env file
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Ticket Tracker - Home",
    page_icon="🎟️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Ticket Tracker - Smart Receipt Management & Analytics"
    }
)

# Custom CSS for modern, aesthetic design
st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Login page styling */
    .login-container {
        max-width: 450px;
        margin: 0 auto;
        padding: 3rem 2rem;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        text-align: center;
        margin-top: 5vh;
    }

    .login-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .login-subtitle {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    .login-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }

    /* Center login button in its column */
    [data-testid="column"]:has(iframe) {
        display: flex;
        justify-content: center;
        align-items: center;
    }

    /* Ensure iframe centers properly */
    [data-testid="column"] iframe {
        margin: 0 auto;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a 0%, #3b82f6 100%);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Hide the Main page link in sidebar nav */
    [data-testid="stSidebarNav"] li:first-child {
        display: none;
    }

    /* User info card */
    .user-card {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.2);
    }

    .user-name {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .user-role {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        margin: 0.2rem;
    }

    /* Logout button */
    .logout-button {
        display: inline-block;
        width: 100%;
        padding: 0.75rem 1.5rem;
        margin-top: 1rem;
        color: white !important;
        background: rgba(255,75,75,0.9);
        border-radius: 10px;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 1rem;
        text-align: center;
        transition: all 0.3s ease;
        border: none;
    }

    .logout-button:hover {
        background: rgba(255,75,75,1);
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255,75,75,0.4);
    }

    /* Navigation styling */
    .nav-section {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.2);
    }

    .nav-title {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1rem;
        opacity: 0.8;
    }

    /* Welcome page styling */
    .welcome-container {
        text-align: center;
        padding: 3rem 2rem;
        max-width: 800px;
        margin: 0 auto;
    }

    .welcome-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }

    .user-email {
        font-size: 0.7rem;
        opacity: 0.8;
        margin-bottom: 0.8rem;
        word-break: break-word;
        max-width: 100%;
    }

    .welcome-subtitle {
        font-size: 1.3rem;
        color: #666;
        margin-bottom: 2rem;
    }

    /* Feature card button styling */
    .stButton > button {
        background: white;
        border-radius: 15px;
        padding: 2rem !important;
        margin: 0 !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        border: 1px solid transparent !important;
        color: #333 !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        text-align: left !important;
        white-space: pre-line !important;
        height: auto !important;
        min-height: 180px !important;
    }

    .stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
        border: 1px solid transparent !important;
    }

    .stButton > button:focus {
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }

    .feature-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #333;
    }

    .feature-desc {
        color: #666;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# OAuth2 Component Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_REDIRECT_URI = "http://localhost:8501"

# Create an OAuth2Component instance
oauth2 = OAuth2Component(
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    authorize_endpoint=f"https://{AUTH0_DOMAIN}/authorize",
    token_endpoint=f"https://{AUTH0_DOMAIN}/oauth/token",
    refresh_token_endpoint=f"https://{AUTH0_DOMAIN}/oauth/token",
    revoke_token_endpoint=f"https://{AUTH0_DOMAIN}/oauth/revoke",
)

# Check if the user is already authenticated
if 'token' not in st.session_state:
    # Login page
    st.markdown("""
    <div class="login-container">
        <div class="login-icon">🎟️</div>
        <div class="login-title">Ticket Tracker</div>
        <div class="login-subtitle">Smart Receipt Management & Analytics</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Center the login button with columns
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        result = oauth2.authorize_button(
            name="🔐 Login with Auth0",
            icon="https://auth0.com/styleguide/components/1.0.8/media/logos/logo-sm.svg",
            redirect_uri=AUTH0_REDIRECT_URI,
            scope="openid email profile",
            key="auth0",
            use_container_width=True,
        )

    if result and "token" in result:
        st.session_state.token = result.get("token")
        st.rerun()

else:
    # User is authenticated - show sidebar with user info and navigation
    token_dict = st.session_state['token']
    id_token = token_dict.get("id_token")

    try:
        # Decode the ID token
        payload = jwt.decode(id_token, options={"verify_signature": False})
        user_name = payload.get("name", "User")
        user_email = payload.get("email", "")

        # Define the namespace used in the Auth0 Action
        namespace = 'https://ticket-tracker.com'
        # Extract roles from the custom claim
        user_roles = payload.get(f'{namespace}/roles', [])

        # Store roles in the session state
        st.session_state['roles'] = user_roles

    except jwt.PyJWTError as e:
        user_name = "User"
        user_email = ""
        user_roles = []
        st.error(f"Could not decode user token: {e}")

    # Sidebar with user info
    with st.sidebar:
        # Display user info only once
        roles_html = ''.join([f'<span class="user-role">{"👑" if role == "admin" else "👤"} {role.title()}</span>' for role in user_roles])

        st.markdown(f"""
        <div class="user-card">
            <div class="user-name">👤 {user_name if user_name and user_name != user_email else user_email.split('@')[0].title()}</div>
            <div class="user-email">{user_email}</div>
            <div>{roles_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation section
        st.markdown('<div class="nav-section"><div class="nav-title">📍 Navigation</div></div>', unsafe_allow_html=True)
        st.info("👈 Use the sidebar to navigate between pages")

        # Logout button
        auth0_domain = os.getenv("AUTH0_DOMAIN")
        auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
        return_to_url = "http://localhost:8501"
        logout_url = f"https://{auth0_domain}/v2/logout?client_id={auth0_client_id}&returnTo={return_to_url}"

        st.markdown(f'<a href="{logout_url}" class="logout-button" target="_self">🚪 Logout</a>', unsafe_allow_html=True)

    # Main welcome page content
    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-title">Welcome, {user_name}! 👋</div>
        <div class="welcome-subtitle">Your intelligent receipt management system</div>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards based on user role
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📤\n\n**Upload Receipts**\n\nUpload receipt images and let AI extract and structure the data automatically", key="upload_card", use_container_width=True):
            st.switch_page("pages/1_Client_Uploader.py")

    with col2:
        if 'admin' in user_roles:
            if st.button("📊\n\n**Admin Dashboard**\n\nQuery expenses with natural language and review OCR quality", key="admin_card", use_container_width=True):
                st.switch_page("pages/2_Admin_Dashboard.py")
        else:
            if st.button("✅\n\n**Track Your Receipts**\n\nView and manage all your uploaded receipts in one place", key="track_card", use_container_width=True):
                st.switch_page("pages/1_Client_Uploader.py")

    if 'admin' in user_roles:
        col3, col4 = st.columns(2)

        with col3:
            if st.button("📈\n\n**Metrics Dashboard**\n\nMonitor AI performance with detailed evaluation metrics", key="metrics_card", use_container_width=True):
                st.switch_page("pages/3_Metrics_Dashboard.py")

        with col4:
            if st.button("🔍\n\n**Quality Review**\n\nReview and correct OCR results to improve accuracy", key="quality_card", use_container_width=True):
                st.switch_page("pages/2_Admin_Dashboard.py")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("💡 **Tip:** Use the navigation menu on the left to access different features!")
