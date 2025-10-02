import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Set page configuration
st.set_page_config(page_title="Metrics Dashboard", layout="wide")

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

# Constants
EVALUATION_SERVICE_URL = "http://evaluation-service:8006"

def fetch_data(endpoint):
    """Fetch data from evaluation service API"""
    try:
        response = requests.get(f"{EVALUATION_SERVICE_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from {endpoint}: {str(e)}")
        return None

def trigger_evaluation(run_type="sample", sample_size=5):
    """Trigger a new evaluation"""
    try:
        if run_type == "sample":
            response = requests.post(
                f"{EVALUATION_SERVICE_URL}/api/v1/evaluation/sample?sample_size={sample_size}",
                timeout=30
            )
        else:  # full evaluation
            response = requests.post(
                f"{EVALUATION_SERVICE_URL}/api/v1/evaluation/run",
                json={"run_type": "manual"},  # Full evaluation uses "manual" type
                timeout=30
            )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to trigger evaluation: {str(e)}")
        return None

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    if not timestamp_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

def show_agent1_metrics():
    """Display Agent 1 (OCR) evaluation metrics"""
    st.header("🧾 Agent 1 (OCR) Evaluation Metrics")

    # Fetch Agent 1 summary metrics
    agent1_summary = fetch_data("/api/v1/metrics/agent1/summary")

    if agent1_summary:
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_evals = agent1_summary.get("total_evaluations", 0)
            st.metric("📊 Total Evaluations", total_evals)

        with col2:
            merchant_match = agent1_summary.get("avg_merchant_match", 0)
            st.metric("🏪 Merchant Match", f"{merchant_match:.1%}")

        with col3:
            amount_match = agent1_summary.get("avg_amount_match", 0)
            st.metric("💰 Amount Match", f"{amount_match:.1%}")

        with col4:
            overall_quality = agent1_summary.get("avg_overall_quality", 0)
            st.metric("⭐ Overall Quality", f"{overall_quality:.1%}")

        st.markdown("---")

        # Token consumption metrics
        st.subheader("🪙 Token Consumption")
        token_col1, token_col2, token_col3 = st.columns(3)

        with token_col1:
            total_tokens = agent1_summary.get("total_tokens_used", 0)
            st.metric("📊 Total Tokens", f"{total_tokens:,}")

        with token_col2:
            avg_tokens = agent1_summary.get("avg_tokens_per_evaluation", 0)
            st.metric("📈 Avg Tokens/Eval", f"{avg_tokens:.0f}")

        with token_col3:
            # Estimate cost (assuming GPT-4o-mini pricing: ~$0.15/1M input, ~$0.60/1M output)
            # Using average of $0.375/1M tokens
            estimated_cost = (total_tokens / 1_000_000) * 0.375
            st.metric("💵 Est. Cost", f"${estimated_cost:.4f}")

        st.markdown("---")

        # Detailed metrics section
        st.subheader("📈 Detailed Metrics")

        metric_col1, metric_col2, metric_col3 = st.columns(3)

        with metric_col1:
            st.write("**Exact Match Metrics**")
            date_match = agent1_summary.get("avg_date_match", 0)
            st.metric("📅 Date Match", f"{date_match:.1%}")
            st.metric("🏪 Merchant Match", f"{merchant_match:.1%}")
            st.metric("💰 Amount Match", f"{amount_match:.1%}")

        with metric_col2:
            st.write("**Item Extraction Metrics**")
            item_precision = agent1_summary.get("avg_item_precision", 0)
            item_recall = agent1_summary.get("avg_item_recall", 0)
            item_f1 = agent1_summary.get("avg_item_f1", 0)
            st.metric("🎯 Precision", f"{item_precision:.1%}")
            st.metric("📚 Recall", f"{item_recall:.1%}")
            st.metric("⚖️ F1 Score", f"{item_f1:.1%}")

        with metric_col3:
            st.write("**LLM-as-a-Judge**")
            merchant_sim = agent1_summary.get("avg_merchant_similarity", 0)
            items_sim = agent1_summary.get("avg_items_similarity", 0)
            st.metric("🔤 Merchant Similarity", f"{merchant_sim:.1%}")
            st.metric("📝 Items Similarity", f"{items_sim:.1%}")
            st.metric("⭐ Overall Quality", f"{overall_quality:.1%}")

        st.markdown("---")

        # Recent runs section
        st.subheader("🏃 Recent Evaluation Runs")
        agent1_runs = fetch_data("/api/v1/metrics/agent1/runs?limit=10")

        if agent1_runs and len(agent1_runs) > 0:
            runs_df = pd.DataFrame(agent1_runs)

            # Format the dataframe for display
            display_df = pd.DataFrame({
                "Run ID": runs_df["run_id"].apply(lambda x: str(x)[:8]),
                "Type": runs_df["run_type"],
                "Status": runs_df["status"],
                "Started": runs_df["started_at"].apply(format_timestamp),
                "Tickets": runs_df["total_tickets"],
                "Success": runs_df["successful_tickets"],
                "Merchant Match": runs_df["average_merchant_match"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"),
                "Amount Match": runs_df["average_amount_match"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"),
                "F1 Score": runs_df["average_item_f1"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"),
                "Overall Quality": runs_df["average_overall_quality"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
            })

            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No Agent 1 evaluation runs found yet. Evaluate tickets from the Admin Dashboard to see metrics here.")

        # Trends chart
        st.subheader("📊 Quality Trends Over Time")

        if agent1_runs and len(agent1_runs) > 0:
            # Filter completed runs with metrics
            completed_runs = [r for r in agent1_runs if r.get("status") == "completed" and r.get("average_overall_quality") is not None]

            if len(completed_runs) > 0:
                trends_df = pd.DataFrame(completed_runs)
                trends_df["started_at"] = pd.to_datetime(trends_df["started_at"])
                trends_df = trends_df.sort_values("started_at")

                fig = go.Figure()

                # Add traces for each metric
                fig.add_trace(go.Scatter(
                    x=trends_df["started_at"],
                    y=trends_df["average_overall_quality"],
                    name="Overall Quality",
                    mode="lines+markers"
                ))

                fig.add_trace(go.Scatter(
                    x=trends_df["started_at"],
                    y=trends_df["average_merchant_match"],
                    name="Merchant Match",
                    mode="lines+markers"
                ))

                fig.add_trace(go.Scatter(
                    x=trends_df["started_at"],
                    y=trends_df["average_amount_match"],
                    name="Amount Match",
                    mode="lines+markers"
                ))

                fig.add_trace(go.Scatter(
                    x=trends_df["started_at"],
                    y=trends_df["average_item_f1"],
                    name="Item F1 Score",
                    mode="lines+markers"
                ))

                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Score",
                    yaxis=dict(range=[0, 1]),
                    hovermode="x unified"
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough completed evaluations to show trends yet.")
        else:
            st.info("No evaluation data available for trends.")
    else:
        st.warning("Failed to fetch Agent 1 metrics from evaluation service.")

def main():
    st.title("📊 Metrics Dashboard")
    st.markdown("Monitor and analyze system performance metrics")

    # Add tabs for different agent evaluations
    metric_category = st.selectbox(
        "📈 Metric Category:",
        ["Agent 1 (OCR)", "Agent 2 (RAG)"],
        help="Select which agent evaluation to view"
    )

    st.markdown("---")

    # Sidebar for controls
    st.sidebar.header("📊 Controls")

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)

    if auto_refresh:
        # Auto-refresh every 30 seconds
        import time
        time.sleep(30)
        st.rerun()

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()

    # === AGENT 1 (OCR) METRICS ===
    if metric_category == "Agent 1 (OCR)":
        show_agent1_metrics()
        return

    # === AGENT 2 (RAG) METRICS ===
    # Trigger evaluation section
    st.sidebar.header("🎯 Trigger Evaluation")

    eval_type = st.sidebar.selectbox(
        "Evaluation Type:",
        ["sample", "full"],
        help="**Sample:** Test with a subset of queries from the test dataset for quick validation\n**Full:** Evaluate all 45 queries from the test dataset (takes ~5-10 minutes)"
    )

    sample_size = 5
    if eval_type == "sample":
        sample_size = st.sidebar.slider(
            "Number of Queries to Evaluate:",
            min_value=1,
            max_value=10,
            value=5,
            help="Randomly select this many queries from the test dataset"
        )
        st.sidebar.caption(f"⚡ Quick test with {sample_size} queries - completes in ~1-2 minutes")
    else:
        st.sidebar.caption("🔄 Full evaluation of all 45 test queries - takes ~5-10 minutes")

    if st.sidebar.button("▶️ Start Evaluation"):
        with st.spinner("Triggering evaluation..."):
            result = trigger_evaluation(eval_type, sample_size)
            if result:
                st.sidebar.success(f"✅ {result['message']}")
                st.sidebar.info("⏳ Evaluation is running in the background. Refresh this page in a few minutes to see results.")
            else:
                st.sidebar.error("❌ Failed to start evaluation")

    # Check for running evaluations
    runs_data = fetch_data("/api/v1/evaluation/runs?limit=10")
    if runs_data:
        running_runs = [run for run in runs_data if run.get('status') == 'running']
        if running_runs:
            st.info(f"🔄 **{len(running_runs)} evaluation(s) currently running.** Results will appear below when complete. Use the refresh button to check for updates.")

    # Main dashboard content
    col1, col2, col3, col4 = st.columns(4)

    # Fetch summary metrics
    summary_data = fetch_data("/api/v1/metrics/summary")

    if summary_data:
        # Key metrics cards
        with col1:
            st.metric(
                label="📈 Total Evaluations",
                value=summary_data.get("total_evaluations", 0),
                delta=None
            )

        with col2:
            success_rate = summary_data.get("success_rate", 0)
            st.metric(
                label="✅ Success Rate",
                value=f"{success_rate:.1f}%",
                delta=None
            )

        with col3:
            latest_faithfulness = summary_data.get("latest_faithfulness")
            if latest_faithfulness is not None:
                st.metric(
                    label="🎯 Latest Faithfulness",
                    value=f"{latest_faithfulness:.3f}",
                    delta=None
                )
            else:
                st.metric(
                    label="🎯 Latest Faithfulness",
                    value="N/A",
                    delta=None
                )

        with col4:
            latest_relevance = summary_data.get("latest_answer_relevance")
            if latest_relevance is not None:
                st.metric(
                    label="🔍 Answer Relevance",
                    value=f"{latest_relevance:.3f}",
                    delta=None
                )
            else:
                st.metric(
                    label="🔍 Answer Relevance",
                    value="N/A",
                    delta=None
                )

    # Token consumption metrics for Agent 2 - Operational Usage
    st.markdown("---")
    st.subheader("🪙 Operational Token Consumption (Agent 2)")
    st.caption("Live token usage from actual user queries (not evaluation)")

    # Fetch operational metrics
    operational_data = fetch_data("/api/v1/metrics/agent2/operational?days=30")

    if operational_data:
        token_col1, token_col2, token_col3, token_col4 = st.columns(4)

        with token_col1:
            total_queries = operational_data.get("total_queries", 0)
            st.metric("📊 Total Queries", f"{total_queries:,}")

        with token_col2:
            total_tokens_operational = operational_data.get("total_tokens", 0)
            st.metric("🔢 Total Tokens", f"{total_tokens_operational:,}")

        with token_col3:
            avg_tokens_operational = operational_data.get("avg_tokens_per_query", 0)
            st.metric("📈 Avg Tokens/Query", f"{avg_tokens_operational:.0f}")

        with token_col4:
            estimated_cost_operational = operational_data.get("estimated_cost", 0)
            st.metric("💵 Est. Cost", f"${estimated_cost_operational:.4f}")

        # Performance metrics
        st.caption(f"⏱️ Avg Response Time: {operational_data.get('avg_response_time_ms', 0):.0f}ms | "
                   f"✅ Success Rate: {(operational_data.get('successful_queries', 0) / max(total_queries, 1) * 100):.1f}%")
    else:
        st.info("No operational query data available yet. Ask Agent 2 some questions to see metrics here!")

    # Agent 2 RAG Evaluation metrics
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Trends", "🏃 Recent Runs", "⚙️ System Status"])

    with tab1:
        st.header("📊 Performance Overview")

        # Fetch recent evaluation runs
        runs_data = fetch_data("/api/v1/evaluation/runs?limit=10")

        if runs_data and len(runs_data) > 0:
            # Create metrics visualization
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🎯 RAGAS Metrics Distribution")

                # Create a radar chart for the latest run with metrics
                latest_run_with_metrics = None
                for run in runs_data:
                    if any([
                        run.get("average_faithfulness"),
                        run.get("average_answer_relevance"),
                        run.get("average_context_precision"),
                        run.get("average_context_recall")
                    ]):
                        latest_run_with_metrics = run
                        break

                if latest_run_with_metrics:
                    metrics = {
                        'Faithfulness': latest_run_with_metrics.get("average_faithfulness", 0) or 0,
                        'Answer Relevance': latest_run_with_metrics.get("average_answer_relevance", 0) or 0,
                        'Context Precision': latest_run_with_metrics.get("average_context_precision", 0) or 0,
                        'Context Recall': latest_run_with_metrics.get("average_context_recall", 0) or 0,
                    }

                    # Radar chart
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=list(metrics.values()),
                        theta=list(metrics.keys()),
                        fill='toself',
                        name='RAGAS Metrics'
                    ))
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 1])
                        ),
                        showlegend=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No evaluation runs with RAGAS metrics available yet. Trigger an evaluation when agent-2-rag is running.")

            with col2:
                st.subheader("📈 Success Rate Over Time")

                # Success rate over time
                df_runs = pd.DataFrame(runs_data)
                df_runs['started_at'] = pd.to_datetime(df_runs['started_at'])
                df_runs['success_rate'] = (df_runs['successful_queries'] / df_runs['total_queries']).fillna(0) * 100
                df_runs = df_runs.sort_values('started_at')

                if len(df_runs) > 0:
                    fig = px.line(
                        df_runs,
                        x='started_at',
                        y='success_rate',
                        title="Success Rate Trend",
                        labels={'success_rate': 'Success Rate (%)', 'started_at': 'Time'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No evaluation runs found. Trigger your first evaluation!")

    with tab2:
        st.header("📈 Historical Trends")

        # Fetch trends data
        days_range = st.selectbox("Time Range:", [7, 14, 30], index=0)
        trends_data = fetch_data(f"/api/v1/metrics/trends?days={days_range}")

        if trends_data and trends_data.get("data_points"):
            df_trends = pd.DataFrame(trends_data["data_points"])
            df_trends['date'] = pd.to_datetime(df_trends['date'])
            df_trends = df_trends.sort_values('date')

            # Multi-line chart for all RAGAS metrics
            fig = go.Figure()

            metrics_to_plot = {
                'faithfulness': '🎯 Faithfulness',
                'answer_relevance': '🔍 Answer Relevance',
                'context_precision': '📍 Context Precision',
                'context_recall': '📚 Context Recall'
            }

            for metric, display_name in metrics_to_plot.items():
                # Filter out null values
                metric_data = df_trends[df_trends[metric].notna()]
                if len(metric_data) > 0:
                    fig.add_trace(go.Scatter(
                        x=metric_data['date'],
                        y=metric_data[metric],
                        mode='lines+markers',
                        name=display_name,
                        line=dict(width=3)
                    ))

            fig.update_layout(
                title="RAGAS Metrics Trends Over Time",
                xaxis_title="Date",
                yaxis_title="Score",
                yaxis=dict(range=[0, 1]),
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Summary statistics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("📊 Summary Statistics")
                for metric, display_name in metrics_to_plot.items():
                    avg_score = df_trends[metric].mean()
                    if not pd.isna(avg_score):
                        st.metric(f"Avg {display_name}", f"{avg_score:.3f}")

            with col2:
                st.subheader("📈 Best Performance")
                for metric, display_name in metrics_to_plot.items():
                    max_score = df_trends[metric].max()
                    if not pd.isna(max_score):
                        st.metric(f"Max {display_name}", f"{max_score:.3f}")

            with col3:
                st.subheader("🔄 Total Evaluations")
                st.metric("Total Runs", len(df_trends))
                st.metric("Total Queries", df_trends['total_queries'].sum())
        else:
            st.info("No trend data available yet. Run more evaluations to see trends!")

    with tab3:
        st.header("🏃 Recent Evaluation Runs")

        # Add filter for run types
        run_type_filter = st.multiselect(
            "Filter by Type:",
            options=["sample", "manual", "realtime"],
            default=["sample", "manual", "realtime"],
            help="Filter evaluation runs by type"
        )

        if runs_data:
            # Filter runs based on selection
            filtered_runs = [run for run in runs_data if run.get('run_type') in run_type_filter]
        else:
            filtered_runs = []

        if filtered_runs:
            # Create a detailed table of recent runs
            runs_df = pd.DataFrame(filtered_runs)

            # Format the DataFrame for display
            display_df = runs_df.copy()
            display_df['started_at'] = display_df['started_at'].apply(format_timestamp)
            display_df['completed_at'] = display_df['completed_at'].apply(format_timestamp)

            # Round numeric columns
            numeric_cols = ['average_faithfulness', 'average_answer_relevance',
                          'average_context_precision', 'average_context_recall']
            for col in numeric_cols:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.3f}" if x is not None else "N/A"
                    )

            # Display the table
            st.dataframe(
                display_df[[
                    'run_type', 'status', 'total_queries', 'successful_queries',
                    'average_faithfulness', 'average_answer_relevance',
                    'average_context_precision', 'average_context_recall',
                    'started_at', 'completed_at'
                ]],
                use_container_width=True
            )

            # Detailed view of selected run
            if len(filtered_runs) > 0:
                st.subheader("🔍 Run Details")
                selected_run_id = st.selectbox(
                    "Select run for detailed results:",
                    options=[run['run_id'] for run in filtered_runs],
                    format_func=lambda x: f"{x[:8]}... ({next(r['run_type'] for r in filtered_runs if r['run_id'] == x)})"
                )

                if selected_run_id:
                    detailed_results = fetch_data(f"/api/v1/evaluation/runs/{selected_run_id}/results")
                    if detailed_results:
                        results_df = pd.DataFrame(detailed_results)

                        # Show summary
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Queries", len(results_df))
                        with col2:
                            successful = len(results_df[results_df['evaluation_status'] == 'success'])
                            st.metric("Successful", successful)
                        with col3:
                            failed = len(results_df[results_df['evaluation_status'] == 'error'])
                            st.metric("Failed", failed)
                        with col4:
                            avg_response_time = results_df['response_time_ms'].mean()
                            st.metric("Avg Response Time", f"{avg_response_time:.0f}ms")

                        # Enhanced query analysis view
                        st.subheader("📋 Query Analysis")

                        # Filter successful queries for detailed analysis
                        successful_queries = results_df[results_df['evaluation_status'] == 'success'].copy()

                        if len(successful_queries) > 0:
                            # Score interpretation helper
                            def interpret_score(score, metric_name):
                                if score is None or pd.isna(score):
                                    return "❓ N/A", "gray"
                                score = float(score)
                                if metric_name in ['faithfulness_score', 'answer_relevance_score']:
                                    if score >= 0.8: return f"🟢 Excellent ({score:.3f})", "green"
                                    elif score >= 0.6: return f"🟡 Good ({score:.3f})", "orange"
                                    elif score >= 0.4: return f"🟠 Fair ({score:.3f})", "orange"
                                    else: return f"🔴 Poor ({score:.3f})", "red"
                                else:  # precision/recall metrics
                                    if score >= 0.7: return f"🟢 High ({score:.3f})", "green"
                                    elif score >= 0.5: return f"🟡 Medium ({score:.3f})", "orange"
                                    elif score >= 0.3: return f"🟠 Low ({score:.3f})", "orange"
                                    else: return f"🔴 Very Low ({score:.3f})", "red"

                            # Query selection for detailed view
                            if len(successful_queries) > 0:
                                selected_query_idx = st.selectbox(
                                    "🔍 Select a query for detailed analysis:",
                                    range(len(successful_queries)),
                                    format_func=lambda x: f"Query {x+1}: {successful_queries.iloc[x]['query_text'][:50]}{'...' if len(successful_queries.iloc[x]['query_text']) > 50 else ''}"
                                )

                                if selected_query_idx is not None:
                                    query_row = successful_queries.iloc[selected_query_idx]

                                    # Display selected query details
                                    st.markdown("### 🎯 Query Analysis Details")

                                    col1, col2 = st.columns([3, 2])

                                    with col1:
                                        st.markdown("**📝 Original Query:**")
                                        st.info(query_row['query_text'])

                                        if query_row['generated_answer']:
                                            st.markdown("**🤖 Generated Answer:**")
                                            st.text_area("", query_row['generated_answer'], height=150, disabled=True)

                                        if query_row['reference_answer']:
                                            st.markdown("**✅ Reference Answer:**")
                                            st.text_area("", query_row['reference_answer'], height=100, disabled=True)

                                    with col2:
                                        st.markdown("**📊 RAGAS Scores:**")

                                        # Faithfulness
                                        faith_text, faith_color = interpret_score(query_row['faithfulness_score'], 'faithfulness_score')
                                        st.markdown(f"**Faithfulness:** {faith_text}")
                                        st.caption("How factually accurate is the answer based on the retrieved context?")

                                        # Answer Relevance
                                        rel_text, rel_color = interpret_score(query_row['answer_relevance_score'], 'answer_relevance_score')
                                        st.markdown(f"**Answer Relevance:** {rel_text}")
                                        st.caption("How well does the answer address the original question?")

                                        # Context Precision
                                        prec_text, prec_color = interpret_score(query_row['context_precision_score'], 'context_precision_score')
                                        st.markdown(f"**Context Precision:** {prec_text}")
                                        st.caption("How much of the retrieved context is relevant to the question?")

                                        # Context Recall
                                        rec_text, rec_color = interpret_score(query_row['context_recall_score'], 'context_recall_score')
                                        st.markdown(f"**Context Recall:** {rec_text}")
                                        st.caption("How much of the relevant information was retrieved?")

                                        # Performance metrics
                                        st.markdown("**⏱️ Performance:**")
                                        st.metric("Response Time", f"{query_row['response_time_ms']}ms")
                                        if query_row['token_count']:
                                            st.metric("Tokens Used", f"{query_row['token_count']}")

                        # Score distribution visualization
                        if len(successful_queries) > 1:
                            st.markdown("### 📊 Score Distribution Analysis")

                            col1, col2 = st.columns(2)

                            with col1:
                                # Create score distribution chart
                                score_cols = ['faithfulness_score', 'answer_relevance_score',
                                            'context_precision_score', 'context_recall_score']

                                fig = go.Figure()

                                for col in score_cols:
                                    scores = successful_queries[col].dropna()
                                    if len(scores) > 0:
                                        fig.add_trace(go.Box(
                                            y=scores,
                                            name=col.replace('_score', '').replace('_', ' ').title(),
                                            boxpoints='all'
                                        ))

                                fig.update_layout(
                                    title="Score Distribution Across Queries",
                                    yaxis_title="Score (0-1)",
                                    yaxis=dict(range=[0, 1])
                                )

                                st.plotly_chart(fig, use_container_width=True)

                            with col2:
                                # Performance analysis
                                st.markdown("**🎯 Performance Summary:**")

                                for col in score_cols:
                                    scores = successful_queries[col].dropna()
                                    if len(scores) > 0:
                                        avg_score = scores.mean()
                                        metric_name = col.replace('_score', '').replace('_', ' ').title()

                                        if avg_score >= 0.7:
                                            st.success(f"🟢 {metric_name}: {avg_score:.3f} (Strong)")
                                        elif avg_score >= 0.5:
                                            st.warning(f"🟡 {metric_name}: {avg_score:.3f} (Moderate)")
                                        else:
                                            st.error(f"🔴 {metric_name}: {avg_score:.3f} (Needs Improvement)")

                        # Raw data table (collapsed by default)
                        with st.expander("🗂️ View Raw Data Table"):
                            st.dataframe(
                                results_df[[
                                    'query_id', 'query_text', 'evaluation_status',
                                    'faithfulness_score', 'answer_relevance_score',
                                    'context_precision_score', 'context_recall_score',
                                    'response_time_ms', 'error_message'
                                ]],
                                use_container_width=True
                            )
        else:
            st.info("No evaluation runs available.")

    with tab4:
        st.header("⚙️ System Status")

        # Health check
        health_data = fetch_data("/health")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏥 Service Health")
            if health_data:
                service_status = health_data.get("status", "unknown")
                if service_status == "healthy":
                    st.success(f"✅ Service Status: {service_status}")
                else:
                    st.warning(f"⚠️ Service Status: {service_status}")

                db_status = health_data.get("database", "unknown")
                if "healthy" in str(db_status):
                    st.success("✅ Database: Connected")
                else:
                    st.error(f"❌ Database: {db_status}")

                st.info(f"Version: {health_data.get('version', 'N/A')}")
            else:
                st.error("❌ Cannot connect to evaluation service")

        with col2:
            st.subheader("📅 Scheduler Status")
            scheduler_data = fetch_data("/api/v1/evaluation/scheduler/status")

            if scheduler_data:
                scheduler_status = scheduler_data.get("status", "unknown")
                if scheduler_status == "running":
                    st.success(f"✅ Scheduler: {scheduler_status}")
                else:
                    st.warning(f"⚠️ Scheduler: {scheduler_status}")

                next_run = scheduler_data.get("next_run")
                if next_run:
                    st.info(f"⏰ Next Run: {format_timestamp(next_run)}")

                jobs = scheduler_data.get("jobs", [])
                st.info(f"📋 Active Jobs: {len(jobs)}")

        # Configuration info
        st.subheader("🔧 Configuration")
        st.code(f"""
Evaluation Service URL: {EVALUATION_SERVICE_URL}
Auto-refresh: {auto_refresh}
Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)

if __name__ == "__main__":
    main()