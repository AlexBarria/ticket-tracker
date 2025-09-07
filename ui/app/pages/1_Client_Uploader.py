# ui/app/pages/1_Client_Uploader.py
import streamlit as st
import requests
import os

st.set_page_config(page_title="Upload Ticket", layout="wide")

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
    st.image(uploaded_file, caption="Uploaded Receipt.", use_column_width=True)
    
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
                    st.success("Receipt processed successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Error processing receipt: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not connect to the processing service: {e}")