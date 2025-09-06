# Basic Streamlit UI application
import streamlit as st
import os

st.set_page_config(page_title="Ticket Tracker Admin", layout="wide")

st.title("Ticket Tracker Admin Dashboard 📈")

st.info("This is a placeholder for the Admin UI where you can ask questions about expenses.")

# Example: Get Agent 2 API URL from environment variables
# agent_api_url = os.getenv("AGENT_2_API_URL", "http://localhost:8003")
# st.sidebar.text(f"API Endpoint: {agent_api_url}")

question = st.text_input("Ask a question about the expense data:")

if st.button("Get Answer"):
    if question:
        # --- MOCK RESPONSE ---
        # In a real scenario, you would make a request to the Agent 2 API
        # import requests
        # response = requests.post(f"{agent_api_url}/ask", json={"query": question})
        # if response.status_code == 200:
        #     st.success(response.json().get("answer"))
        # else:
        #     st.error("Failed to get an answer from the agent.")
        st.success(f"Mock Answer for: '{question}'\n\nUser A spent $100 in restaurants in July 2025.")
    else:
        st.warning("Please enter a question.")