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
tab1, tab2 = st.tabs(["💬 LLM Chat", "📝 Ticket Review & Correction"])

with tab1:
    st.subheader("LLM Chat (Ask about expenses)")
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


# --- Agent 1 (OCR) Evaluation Section ---
with tab2:
    st.subheader("Ticket Review & Correction")
    st.info("Evaluate the OCR quality of uploaded receipts by providing the correct values.")

    # Fetch recent tickets for evaluation
    try:
        with st.spinner("Loading recent tickets..."):
            id_token = st.session_state['token']['id_token']

            # Fetch recent tickets from database
            tickets_response = requests.get(
                "http://agent-1-formatter:8000/api/tickets",  # Assuming this endpoint exists
                headers={"Authorization": f"Bearer {id_token}"},
                params={"limit": 10, "need_verify": True}
            )

            if tickets_response.status_code == 200:
                tickets = tickets_response.json()
                # If backend does not filter, do it here:
                tickets = [t for t in tickets if t.get('need_verify', False)]

                if tickets:
                    # Let user select a ticket to evaluate
                    ticket_options = {
                        f"ID {t['id']} - {t['merchant_name']} (${t['total_amount']})": t['id']
                        for t in tickets
                    }

                    selected_ticket_label = st.selectbox(
                        "Select a ticket to evaluate:",
                        options=list(ticket_options.keys())
                    )

                    selected_ticket_id = ticket_options[selected_ticket_label]

                    # Find the selected ticket data
                    selected_ticket = next(t for t in tickets if t['id'] == selected_ticket_id)

                    # Display OCR output
                    st.subheader("📄 OCR Output (Agent 1)")
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Merchant:** {selected_ticket.get('merchant_name', 'N/A')}")
                        st.write(f"**Date:** {selected_ticket.get('transaction_date', 'N/A')}")
                        st.write(f"**Amount:** ${selected_ticket.get('total_amount', 0):.2f}")

                        # Show receipt image from MinIO
                        s3_path = selected_ticket.get('s3_path')
                        if s3_path:
                            image_api_url = f"http://localhost:8002/api/image?s3_path={s3_path}"
                            st.image(image_api_url, caption="Receipt Image", use_container_width=True)
                        else:
                            st.info("No image available for this ticket.")

                    with col2:
                        st.write("**Items:**")
                        items = selected_ticket.get('items', [])
                        if items:
                            for item in items:
                                st.write(f"- {item.get('description', 'Unknown')}: ${item.get('price', 0):.2f}")
                        else:
                            st.write("No items")

                    # Evaluation form
                    st.subheader("✅ Provide Correct Values")

                    with st.form("agent1_eval_form"):
                        expected_merchant = st.text_input(
                            "Correct Merchant Name:",
                            value=selected_ticket.get('merchant_name', ''),
                            help="Enter the correct merchant name as it appears on the receipt"
                        )

                        expected_date = st.date_input(
                            "Correct Transaction Date:",
                            help="Select the correct date from the receipt"
                        )

                        expected_amount = st.number_input(
                            "Correct Total Amount:",
                            min_value=0.0,
                            value=float(selected_ticket.get('total_amount', 0)),
                            step=0.01,
                            format="%.2f",
                            help="Enter the correct total amount"
                        )

                        st.write("**Correct Items:**")
                        st.caption("Enter the items as they appear on the receipt")

                        num_items = st.number_input("Number of items:", min_value=0, max_value=20, value=len(items))

                        expected_items = []
                        for i in range(int(num_items)):
                            item_col1, item_col2 = st.columns([3, 1])
                            with item_col1:
                                item_desc = st.text_input(
                                    f"Item {i+1} Description:",
                                    value=items[i].get('description', '') if i < len(items) else '',
                                    key=f"item_desc_{i}"
                                )
                            with item_col2:
                                item_price = st.number_input(
                                    f"Price:",
                                    min_value=0.0,
                                    value=float(items[i].get('price', 0)) if i < len(items) else 0.0,
                                    step=0.01,
                                    format="%.2f",
                                    key=f"item_price_{i}"
                                )

                            if item_desc:  # Only add if description is provided
                                expected_items.append({
                                    "description": item_desc,
                                    "price": item_price
                                })

                        submit_eval = st.form_submit_button("🔍 Evaluate OCR Quality", type="primary")

                    if submit_eval:
                        with st.spinner("Evaluating OCR quality..."):
                            try:
                                eval_response = requests.post(
                                    "http://evaluation-service:8006/api/v1/evaluation/agent1/realtime",
                                    json={
                                        "ticket_id": selected_ticket_id,
                                        "expected_merchant": expected_merchant,
                                        "expected_date": str(expected_date),
                                        "expected_amount": expected_amount,
                                        "expected_items": expected_items
                                    },
                                    timeout=60
                                )

                                if eval_response.status_code == 200:
                                    eval_data = eval_response.json()

                                    st.success("✅ OCR quality evaluated successfully!")

                                    # Display metrics
                                    st.subheader("📊 Evaluation Metrics")

                                    metrics = eval_data.get('metrics', {})

                                    # Deterministic metrics
                                    st.write("**Exact Match Metrics:**")
                                    det_col1, det_col2, det_col3 = st.columns(3)

                                    with det_col1:
                                        merchant_match = metrics.get('merchant_match')
                                        st.metric("Merchant Match", "✅ Yes" if merchant_match else "❌ No")

                                    with det_col2:
                                        date_match = metrics.get('date_match')
                                        st.metric("Date Match", "✅ Yes" if date_match else "❌ No")

                                    with det_col3:
                                        amount_match = metrics.get('amount_match')
                                        st.metric("Amount Match", "✅ Yes" if amount_match else "❌ No")

                                    # Item metrics
                                    st.write("**Item Extraction Metrics:**")
                                    item_col1, item_col2, item_col3 = st.columns(3)

                                    with item_col1:
                                        precision = metrics.get('item_precision')
                                        if precision is not None:
                                            st.metric("Precision", f"{precision:.2%}")

                                    with item_col2:
                                        recall = metrics.get('item_recall')
                                        if recall is not None:
                                            st.metric("Recall", f"{recall:.2%}")

                                    with item_col3:
                                        f1 = metrics.get('item_f1')
                                        if f1 is not None:
                                            st.metric("F1 Score", f"{f1:.2%}")

                                    # LLM-as-judge metrics
                                    st.write("**LLM Quality Assessment:**")
                                    llm_col1, llm_col2, llm_col3 = st.columns(3)

                                    with llm_col1:
                                        merchant_sim = metrics.get('merchant_similarity')
                                        if merchant_sim is not None:
                                            st.metric("Merchant Similarity", f"{merchant_sim:.2%}")

                                    with llm_col2:
                                        items_sim = metrics.get('items_similarity')
                                        if items_sim is not None:
                                            st.metric("Items Similarity", f"{items_sim:.2%}")

                                    with llm_col3:
                                        overall = metrics.get('overall_quality')
                                        if overall is not None:
                                            st.metric("Overall Quality", f"{overall:.2%}")

                                    # LLM Feedback
                                    llm_feedback = eval_data.get('llm_feedback')
                                    if llm_feedback:
                                        st.info(f"**LLM Feedback:** {llm_feedback}")

                                    # Show comparison
                                    with st.expander("📋 Detailed Comparison"):
                                        expected = eval_data.get('expected', {})
                                        actual = eval_data.get('actual', {})

                                        comp_col1, comp_col2 = st.columns(2)

                                        with comp_col1:
                                            st.write("**Expected (Ground Truth):**")
                                            st.json(expected)

                                        with comp_col2:
                                            st.write("**Actual (OCR Output):**")
                                            st.json(actual)

                                    # Save ground truth and auto-approve
                                    try:
                                        save_gt_response = requests.post(
                                            "http://agent-1-formatter:8000/api/save-ground-truth",
                                            headers={"Authorization": f"Bearer {id_token}"},
                                            json={
                                                "ticket_id": selected_ticket_id,
                                                "corrected_merchant": expected_merchant,
                                                "corrected_date": str(expected_date),
                                                "corrected_amount": expected_amount,
                                                "corrected_items": expected_items
                                            }
                                        )

                                        if save_gt_response.status_code == 200:
                                            st.success("✅ Evaluation saved! Ground truth recorded and ticket approved. View aggregate metrics in the Metrics Dashboard.")
                                            st.info("This ticket will no longer appear in the review queue.")
                                        else:
                                            st.warning(f"Evaluation saved but failed to save ground truth: {save_gt_response.status_code}")
                                    except Exception as gt_error:
                                        st.warning(f"Evaluation saved but failed to save ground truth: {str(gt_error)}")

                                else:
                                    st.error(f"❌ Evaluation failed: {eval_response.status_code}")
                                    st.error(eval_response.text)

                            except Exception as e:
                                st.error(f"❌ Evaluation error: {str(e)}")

                else:
                    st.warning("No tickets found. Upload some receipts first in the Client Uploader page.")

            else:
                st.error(f"Failed to fetch tickets: {tickets_response.status_code}")

    except Exception as e:
        st.error(f"Error loading tickets: {str(e)}")