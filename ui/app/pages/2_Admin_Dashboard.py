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

# Add evaluation option
col1, col2 = st.columns([3, 1])
with col1:
    submit_button = st.button("Get Answer", type="primary")
with col2:
    evaluate_query = st.checkbox("📊 Evaluate Quality", help="Evaluate this query using RAGAS metrics and add to evaluation dataset")

# Optional reference answer for evaluation
reference_answer = ""
if evaluate_query:
    reference_answer = st.text_area(
        "Expected Answer (Optional):",
        help="Provide the expected answer for better evaluation metrics. If left empty, evaluation will still run but context recall may be less accurate.",
        height=100
    )

if submit_button:
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
                    answer = response.json().get('answer')
                    st.success(f"**Answer:** {answer}")

                    # If evaluation is enabled, trigger evaluation
                    if evaluate_query:
                        st.markdown("---")
                        st.subheader("📊 Evaluation Results")

                        with st.spinner("Evaluating query quality with RAGAS metrics..."):
                            try:
                                eval_response = requests.post(
                                    "http://evaluation-service:8006/api/v1/evaluation/realtime",
                                    json={
                                        "question": question,
                                        "reference_answer": reference_answer
                                    },
                                    timeout=60
                                )

                                if eval_response.status_code == 200:
                                    eval_data = eval_response.json()

                                    # Display metrics in columns
                                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

                                    with metric_col1:
                                        faith_score = eval_data.get('faithfulness_score')
                                        if faith_score is not None:
                                            st.metric("🎯 Faithfulness", f"{faith_score:.3f}")
                                        else:
                                            st.metric("🎯 Faithfulness", "N/A")

                                    with metric_col2:
                                        rel_score = eval_data.get('answer_relevance_score')
                                        if rel_score is not None:
                                            st.metric("🔍 Relevance", f"{rel_score:.3f}")
                                        else:
                                            st.metric("🔍 Relevance", "N/A")

                                    with metric_col3:
                                        prec_score = eval_data.get('context_precision_score')
                                        if prec_score is not None:
                                            st.metric("📍 Precision", f"{prec_score:.3f}")
                                        else:
                                            st.metric("📍 Precision", "N/A")

                                    with metric_col4:
                                        rec_score = eval_data.get('context_recall_score')
                                        if rec_score is not None:
                                            st.metric("📚 Recall", f"{rec_score:.3f}")
                                        else:
                                            st.metric("📚 Recall", "N/A")

                                    # Show response time
                                    response_time = eval_data.get('response_time_ms')
                                    if response_time:
                                        st.caption(f"⏱️ Response Time: {response_time}ms")

                                    st.success("✅ Query evaluated and added to evaluation dataset. View details in Metrics Dashboard.")

                                    # Add info box explaining metrics
                                    with st.expander("ℹ️ Understanding the Metrics"):
                                        st.markdown("""
                                        **Faithfulness (0-1):** How factually accurate is the answer based on the retrieved context?
                                        - Higher is better (0.8+ is excellent)

                                        **Answer Relevance (0-1):** How well does the answer address the original question?
                                        - Higher is better (0.8+ is excellent)

                                        **Context Precision (0-1):** How much of the retrieved context is relevant?
                                        - Higher means less irrelevant information (0.7+ is good)

                                        **Context Recall (0-1):** How much of the relevant information was retrieved?
                                        - Higher means better information retrieval (0.7+ is good)
                                        """)
                                else:
                                    st.warning(f"⚠️ Evaluation failed: {eval_response.status_code}")

                            except requests.exceptions.Timeout:
                                st.error("⏱️ Evaluation timed out. The query was answered but evaluation could not complete.")
                            except Exception as eval_error:
                                st.error(f"❌ Evaluation error: {eval_error}")

                else:
                    st.error("Failed to get an answer from the agent.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a question.")