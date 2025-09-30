# ui/app/pages/3_Metrics_Dashboard.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Set page configuration
st.set_page_config(page_title="Metrics Dashboard", layout="wide")

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

def main():
    st.title("📊 Metrics Dashboard")
    st.markdown("Monitor and analyze system performance metrics")

    # Add tabs for different metric categories - ready for future expansion
    metric_category = st.selectbox(
        "📈 Metric Category:",
        ["🎯 RAGAS Evaluation", "📊 System Performance", "📈 Usage Analytics"],
        help="Select the type of metrics to view"
    )

    # Currently only RAGAS is implemented
    if metric_category != "🎯 RAGAS Evaluation":
        st.info(f"🚧 {metric_category} metrics coming soon! Currently showing RAGAS evaluation metrics.")

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

    # Create two main sections
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