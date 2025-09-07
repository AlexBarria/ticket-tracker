# ui/app/pages/2_Admin_Dashboard.py
import streamlit as st

st.set_page_config(page_title="Admin Dashboard", layout="wide")

# --- Security Guard ---
# Check if the user is logged in
if 'token' not in st.session_state:
    st.warning("Please log in to access this page.")
    st.stop() # Stop further execution of the page

# --- Page Content ---
st.title("Admin Dashboard 📈")
st.info("Ask a question about the expense data in natural language.")

question = st.text_input("For example: 'How much did we spend on restaurants in July?'")

if st.button("Get Answer"):
    if question:
        with st.spinner("Searching for an answer..."):
            # --- Placeholder for API call ---
            # In the future, we will make a request to the Agent 2 API
            # import requests
            # headers = {'Authorization': f'Bearer {st.session_state["token"]["access_token"]}'}
            # response = requests.post("http://agent-2-rag:8000/ask", json={"query": question}, headers=headers)
            # if response.status_code == 200:
            #     st.success(f"**Answer:** {response.json().get('answer')}")
            # else:
            #     st.error("Failed to get an answer from the agent.")
            
            # Mock response for now
            import time
            time.sleep(2)
            st.success("**Answer:** User A spent $100 in restaurants in July 2025, across 3 receipts.")
    else:
        st.warning("Please enter a question.")