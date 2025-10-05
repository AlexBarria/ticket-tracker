"""
Client Uploader Page, allows clients to upload ticket images for processing.
"""
import streamlit as st
import requests
import json

st.set_page_config(page_title="Upload Ticket", layout="wide")

# Apply consistent blue sidebar styling
st.markdown("""
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a 0%, #3b82f6 100%);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Sidebar buttons - make them visible with background */
    [data-testid="stSidebar"] button {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stSidebar"] button:hover {
        background-color: rgba(255, 255, 255, 0.3) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
    }

    [data-testid="stSidebar"] button p {
        color: white !important;
    }

    /* Sidebar selectbox - make them visible */
    [data-testid="stSidebar"] [data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: transparent !important;
        color: white !important;
    }

    /* Sidebar slider */
    [data-testid="stSidebar"] [data-testid="stSlider"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        padding: 0.5rem;
        border-radius: 0.5rem;
    }

    /* Make selectbox options readable */
    [data-baseweb="popover"] {
        background-color: white !important;
    }

    [data-baseweb="popover"] * {
        color: #1f2937 !important;
    }

    /* Fix main content buttons - ensure text is visible */
    div[data-testid="stMainBlockContainer"] button {
        color: #1f2937 !important;
    }

    div[data-testid="stMainBlockContainer"] button:hover {
        color: #111827 !important;
    }

    /* Ensure button text in main area is dark */
    div[data-testid="stMainBlockContainer"] .stButton > button p {
        color: #1f2937 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Security Guard ---
# Check if the user is logged in
if 'token' not in st.session_state:
    st.warning("Please log in to access this page.")
    st.stop()

# Check for the correct role to access the page
user_roles = st.session_state.get('roles', [])
if 'client' not in user_roles and 'admin' not in user_roles:
    st.error("🚫 You do not have permission to view this page.")
    st.stop()

# --- Page Content ---
st.title("📄 Upload Your Receipt")
st.write("Use the uploader below to submit a photo of your ticket or receipt.")

uploaded_file = st.file_uploader(
    "Choose a receipt image...",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Receipt.", use_container_width=True)

    if st.button("Process Receipt"):
        with st.spinner("Uploading and processing..."):
            # Get the ID token from the session state, which is a JWT
            id_token = st.session_state['token']['id_token']

            # Prepare the request to Agent 1
            agent_1_url = "http://agent-1-formatter:8000/upload-receipt/"
            headers = {"Authorization": f"Bearer {id_token}"}
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

            try:
                response = requests.post(agent_1_url, headers=headers, files=files)
                if response.status_code == 200:
                    st.session_state['receipt_response'] = response.json()
                    st.session_state['uploaded_file'] = uploaded_file
                else:
                    st.error(f"Error processing receipt: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to the processing service: {e}")

if 'receipt_response' in st.session_state:
    st.success("Receipt processed successfully!")
    st.json(st.session_state['receipt_response'])

    acknowledged = st.checkbox("I acknowledge that the data is correct")
    ticket_id_payload = json.dumps({"id": st.session_state['receipt_response'].get("id")}).encode("utf-8")
    id_token = st.session_state['token']['id_token']
    headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
    approve_url = "http://agent-1-formatter:8000/approve-receipt/"
    verify_url = "http://agent-1-formatter:8000/verify-receipt/"
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Accept", disabled=not acknowledged):
            try:
                approve_response = requests.post(approve_url, data=ticket_id_payload, headers=headers)
                if approve_response.status_code == 200:
                    st.success("Receipt approved successfully!")
                else:
                    st.error(f"Error approving receipt: {approve_response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to the approval service: {e}")
    with col2:
        if st.button("❌ Verify"):
            try:
                verify_response = requests.post(verify_url, data=ticket_id_payload, headers=headers)
                if verify_response.status_code == 200:
                    st.success("Verification requested successfully!")
                else:
                    st.error(f"Error requesting verification: {verify_response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to the verification service: {e}")

                st.json(response.json())
