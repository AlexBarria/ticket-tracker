import requests
import streamlit as st
from datetime import date

st.set_page_config(page_title="Admin Dashboard", layout="wide")

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
if 'admin' not in user_roles:
    st.error("🚫 You do not have permission to view this page. This area is for administrators only.")
    st.stop()

# --- Page Content ---
st.title("Admin Dashboard 📈")
tab1, tab2, tab3 = st.tabs(["💬 LLM Chat", "📝 Ticket Review & Correction", "🗄️ Database Viewer"])

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
                            min_value=date(2000, 1, 1),
                            max_value=date.today(),
                            help="Select the correct date from the receipt (from year 2000 to today)"
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
                                    st.write("**LLM as a Judge:**")
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
                                        st.info(f"**LLM-as-a-Jugde Feedback:** {llm_feedback}")

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


# --- Database Viewer Tab ---
with tab3:
    st.subheader("🗄️ Database Viewer")
    st.info("View all tickets, filter by status, see images, and analyze spending trends.")

    try:
        id_token = st.session_state['token']['id_token']

        # Fetch all tickets from database
        with st.spinner("Loading tickets from database..."):
            all_tickets_response = requests.get(
                "http://agent-1-formatter:8000/api/tickets/all",
                headers={"Authorization": f"Bearer {id_token}"}
            )

        if all_tickets_response.status_code == 200:
            all_tickets = all_tickets_response.json()

            if all_tickets:
                # === STATISTICS SECTION ===
                st.markdown("### 📊 Overall Statistics")

                # Calculate statistics
                total_tickets = len(all_tickets)
                approved_tickets = sum(1 for t in all_tickets if t.get('approved'))
                needs_review = sum(1 for t in all_tickets if t.get('need_verify'))
                total_spent = sum(float(t.get('total_amount', 0)) for t in all_tickets)

                # Display metrics
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                with metric_col1:
                    st.metric("📝 Total Tickets", total_tickets)
                with metric_col2:
                    st.metric("✅ Approved", approved_tickets)
                with metric_col3:
                    st.metric("⚠️ Needs Review", needs_review)
                with metric_col4:
                    st.metric("💰 Total Spent", f"${total_spent:,.2f}")

                st.markdown("---")

                # === TRENDS SECTION ===
                st.markdown("### 📈 Spending Trends")

                trend_col1, trend_col2 = st.columns(2)

                with trend_col1:
                    # Top spending users
                    st.markdown("#### 👤 Top Spenders")
                    user_spending = {}
                    for ticket in all_tickets:
                        user_id = ticket.get('user_id', 'Unknown')
                        amount = float(ticket.get('total_amount', 0))
                        user_spending[user_id] = user_spending.get(user_id, 0) + amount

                    # Sort and display top 5
                    top_users = sorted(user_spending.items(), key=lambda x: x[1], reverse=True)[:5]
                    for idx, (user, amount) in enumerate(top_users, 1):
                        # Shorten user ID for display
                        display_user = user[:20] + "..." if len(user) > 20 else user
                        st.write(f"{idx}. **{display_user}**: ${amount:,.2f}")

                with trend_col2:
                    # Top spending categories
                    st.markdown("#### 🏷️ Top Categories")
                    category_spending = {}
                    for ticket in all_tickets:
                        category = ticket.get('category', 'Uncategorized')
                        amount = float(ticket.get('total_amount', 0))
                        category_spending[category] = category_spending.get(category, 0) + amount

                    # Sort and display top 5
                    top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
                    for idx, (cat, amount) in enumerate(top_categories, 1):
                        st.write(f"{idx}. **{cat}**: ${amount:,.2f}")

                st.markdown("---")

                # === FILTERS SECTION ===
                st.markdown("### 🔍 Filter Tickets")

                filter_col1, filter_col2, filter_col3 = st.columns(3)

                with filter_col1:
                    status_filter = st.selectbox(
                        "Approval Status",
                        ["All", "Approved", "Not Approved", "Needs Review"]
                    )

                with filter_col2:
                    # Get unique categories
                    categories = sorted(set(t.get('category', 'Uncategorized') for t in all_tickets))
                    category_filter = st.selectbox(
                        "Category",
                        ["All"] + categories
                    )

                with filter_col3:
                    # Get unique users
                    users = sorted(set(t.get('user_id', 'Unknown') for t in all_tickets))
                    user_display = ["All"] + [u[:30] + "..." if len(u) > 30 else u for u in users]
                    user_filter = st.selectbox("User", user_display)

                # Apply filters
                filtered_tickets = all_tickets.copy()

                if status_filter == "Approved":
                    filtered_tickets = [t for t in filtered_tickets if t.get('approved')]
                elif status_filter == "Not Approved":
                    filtered_tickets = [t for t in filtered_tickets if not t.get('approved')]
                elif status_filter == "Needs Review":
                    filtered_tickets = [t for t in filtered_tickets if t.get('need_verify')]

                if category_filter != "All":
                    filtered_tickets = [t for t in filtered_tickets if t.get('category') == category_filter]

                if user_filter != "All":
                    # Find the actual user ID from the display name
                    actual_user = users[user_display.index(user_filter) - 1] if user_filter != "All" else None
                    if actual_user:
                        filtered_tickets = [t for t in filtered_tickets if t.get('user_id') == actual_user]

                st.markdown(f"### 📋 Tickets ({len(filtered_tickets)} results)")

                # === TICKETS TABLE ===
                if filtered_tickets:
                    # Sort by ID descending (most recent first)
                    filtered_tickets = sorted(filtered_tickets, key=lambda x: x.get('id', 0), reverse=True)

                    # Display tickets in expandable sections
                    for ticket in filtered_tickets:
                        ticket_id = ticket.get('id', 'N/A')
                        merchant = ticket.get('merchant_name', 'Unknown')
                        amount = ticket.get('total_amount', 0)
                        date = ticket.get('transaction_date', 'N/A')
                        approved = ticket.get('approved', False)
                        needs_verify = ticket.get('need_verify', False)
                        category = ticket.get('category', 'Uncategorized')

                        # Status badge
                        if approved:
                            status_badge = "✅ Approved"
                            status_color = "green"
                        elif needs_verify:
                            status_badge = "⚠️ Needs Review"
                            status_color = "orange"
                        else:
                            status_badge = "❌ Not Approved"
                            status_color = "red"

                        # Create expander for each ticket
                        with st.expander(f"**#{ticket_id}** | {merchant} | ${amount:.2f} | {date} | {status_badge}"):
                            ticket_col1, ticket_col2 = st.columns([1, 1])

                            with ticket_col1:
                                st.markdown("**Ticket Details**")
                                st.write(f"**ID:** {ticket_id}")
                                st.write(f"**Merchant:** {merchant}")
                                st.write(f"**Date:** {date}")
                                st.write(f"**Amount:** ${amount:.2f}")
                                st.write(f"**Category:** {category}")
                                st.write(f"**Status:** {status_badge}")

                                # User ID (shortened)
                                user_id = ticket.get('user_id', 'Unknown')
                                display_user_id = user_id[:40] + "..." if len(user_id) > 40 else user_id
                                st.write(f"**User:** {display_user_id}")

                                # Items
                                st.markdown("**Items:**")
                                items = ticket.get('items', [])
                                if items:
                                    for item in items:
                                        desc = item.get('description', 'Unknown')
                                        price = item.get('price', 0)
                                        st.write(f"- {desc}: ${price:.2f}")
                                else:
                                    st.write("_No items_")

                            with ticket_col2:
                                # Display receipt image from MinIO
                                s3_path = ticket.get('s3_path')
                                if s3_path:
                                    try:
                                        image_api_url = f"http://localhost:8002/api/image?s3_path={s3_path}"
                                        st.image(image_api_url, caption="Receipt Image", use_container_width=True)
                                    except:
                                        st.info("📷 Image preview unavailable")
                                else:
                                    st.info("📷 No image available for this ticket")

                else:
                    st.warning("No tickets match the selected filters.")

            else:
                st.warning("No tickets found in the database. Upload some receipts first!")

        else:
            st.error(f"Failed to fetch tickets: {all_tickets_response.status_code}")

    except Exception as e:
        st.error(f"Error loading database viewer: {str(e)}")