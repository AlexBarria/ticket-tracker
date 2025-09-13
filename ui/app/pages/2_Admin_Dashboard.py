# ui/app/pages/2_Admin_Dashboard.py
import requests
import streamlit as st

st.set_page_config(page_title="Admin Dashboard", layout="wide")

# --- Security Guard ---
# Check if the user is logged in
if 'token' not in st.session_state:
    st.warning("Please log in to access this page.")
    st.stop()

# Check for the correct role to access the page
user_roles = st.session_state.get('roles', [])
if 'admin' not in user_roles:
    st.error("🚫 You do not have permission to view this page. This area is for administrators only.")
    st.stop()

# --- Page Content ---
st.title("Admin Dashboard 📈")
st.info("Ask a question about the expense data in natural language.")

question = st.text_input("For example: 'How much did we spend on restaurants in July?'")

if st.button("Get Answer"):
    if question:
        with st.spinner("Searching for an answer..."):
            # Get the ID token from the session state, which is a JWT
            id_token = st.session_state['token']['id_token']

            # Prepare the request to Agent 2
            agent_2_url = "http://agent-2-rag:8000/ask"
            headers = {"Authorization": f"Bearer {id_token}"}
            try:
                response = requests.post(agent_2_url, json={"query": question}, headers=headers)
                if response.status_code == 200:
                    st.success(f"**Answer:** {response.json().get('answer')}")
                else:
                    st.error("Failed to get an answer from the agent.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a question.")