# ui/app/main.py
import streamlit as st
import os
from streamlit_oauth import OAuth2Component
from dotenv import load_dotenv
import jwt

# Load environment variables from .env file
load_dotenv()

# Set page configuration
st.set_page_config(page_title="Ticket Tracker Login", layout="centered")

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
    st.title("Welcome to Ticket Tracker 🎟️")
    st.write("Please log in to continue.")
    result = oauth2.authorize_button(
        name="Login with Auth0",
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
    # If authenticated, show user info and a logout button
    token_dict = st.session_state['token']
    id_token = token_dict.get("id_token")
    
    try:
        # Decode the ID token without verifying the signature for this simple display.
        payload = jwt.decode(id_token, options={"verify_signature": False})
        user_name = payload.get("name", "User") # Extract the name from the JWT payload
    except jwt.PyJWTError as e:
        user_name = "User"
        st.error(f"Could not decode user token: {e}")

    st.title(f"Welcome, {user_name}!")
    st.write("You are logged in.")
    st.write("Select a page from the sidebar to get started.")
    
    # For debugging, we can show the entire token content:
    # st.expander("Token Details").write(token_dict)
    

    auth0_domain = os.getenv("AUTH0_DOMAIN")
    auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
    return_to_url = "http://localhost:8501" 
    
    # Construct the correct logout URL
    logout_url = f"https://{auth0_domain}/v2/logout?client_id={auth0_client_id}&returnTo={return_to_url}"

    # Use CSS to make the link look like a Streamlit button
    st.markdown("""
    <style>
    .logout-button {
        display: inline-block;
        padding: 0.5em 1em;
        color: white !important;
        background-color: #FF4B4B; /* Color rojo de Streamlit */
        border-radius: 0.25rem;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .logout-button:hover {
        background-color: #FF6B6B;
    }
    </style>
    """, unsafe_allow_html=True)

    # Creamos el enlace de logout con la clase CSS
    st.markdown(f'<a href="{logout_url}" class="logout-button" target="_self">Logout</a>', unsafe_allow_html=True)