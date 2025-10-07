from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import math

from ..database import get_db, EvaluationDB, EvaluationRun, EvaluationResult, Agent1EvaluationRun, Agent1EvaluationResult
from pydantic import BaseModel

router = APIRouter()


def safe_float(value):
    """Convert NaN and infinity values to None for JSON serialization"""
    import math
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    return value


# Response models
class MetricsSummaryResponse(BaseModel):
    latest_run_id: Optional[str]
    latest_run_date: Optional[datetime]
    total_evaluations: int
    successful_evaluations: int
    success_rate: float

    # Latest metrics
    latest_faithfulness: Optional[float]
    latest_answer_relevance: Optional[float]
    latest_context_precision: Optional[float]
    latest_context_recall: Optional[float]

    # Overall averages
    avg_faithfulness: Optional[float]
    avg_answer_relevance: Optional[float]
    avg_context_precision: Optional[float]
    avg_context_recall: Optional[float]
    avg_response_time_ms: Optional[float]

    # Token consumption metrics
    total_tokens: Optional[int] = 0
    avg_tokens_per_query: Optional[float] = 0

    class Config:
        json_encoders = {
            float: lambda v: None if (v is not None and (math.isnan(v) or math.isinf(v))) else v
        }


class TrendDataPoint(BaseModel):
    date: datetime
    run_id: str
    faithfulness: Optional[float]
    answer_relevance: Optional[float]
    context_precision: Optional[float]
    context_recall: Optional[float]
    total_queries: Optional[int]
    successful_queries: Optional[int]
    success_rate: Optional[float]

    class Config:
        json_encoders = {
            float: lambda v: None if (v is not None and (math.isnan(v) or math.isinf(v))) else v
        }


class MetricsTrendsResponse(BaseModel):
    period_days: int
    data_points: List[TrendDataPoint]


class DetailedMetricsResponse(BaseModel):
    run_id: str
    run_date: datetime
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float

    # RAGAS metrics
    faithfulness: Optional[float]
    answer_relevance: Optional[float]
    context_precision: Optional[float]
    context_recall: Optional[float]

    # Performance metrics
    avg_response_time_ms: Optional[float]
    total_tokens: Optional[int]
    avg_tokens_per_query: Optional[float]

    # Query breakdown
    query_status_breakdown: Dict[str, int]


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(db: Session = Depends(get_db)):
    """
    Get summary of latest evaluation metrics
    """
    try:
        eval_db = EvaluationDB(db)

        # Get latest completed run
        latest_run = eval_db.get_latest_metrics()

        # Get overall statistics
        completed_runs = db.query(EvaluationRun).filter(
            EvaluationRun.status == "completed"
        ).all()

        total_evaluations = 0
        successful_evaluations = 0

        faithfulness_scores = []
        answer_relevance_scores = []
        context_precision_scores = []
        context_recall_scores = []
        response_times = []

        for run in completed_runs:
            if run.total_queries:
                total_evaluations += run.total_queries
            if run.successful_queries:
                successful_evaluations += run.successful_queries

            # Collect metric scores for averaging
            safe_faithfulness = safe_float(run.average_faithfulness)
            if safe_faithfulness is not None:
                faithfulness_scores.append(safe_faithfulness)
            safe_answer_relevance = safe_float(run.average_answer_relevance)
            if safe_answer_relevance is not None:
                answer_relevance_scores.append(safe_answer_relevance)
            safe_context_precision = safe_float(run.average_context_precision)
            if safe_context_precision is not None:
                context_precision_scores.append(safe_context_precision)
            safe_context_recall = safe_float(run.average_context_recall)
            if safe_context_recall is not None:
                context_recall_scores.append(safe_context_recall)

        # Get average response times from results
        avg_response_time = db.query(func.avg(EvaluationResult.response_time_ms)).filter(
            EvaluationResult.evaluation_status == "success"
        ).scalar()

        success_rate = (successful_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0

        # Calculate overall averages
        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else None
        avg_answer_relevance = sum(answer_relevance_scores) / len(answer_relevance_scores) if answer_relevance_scores else None
        avg_context_precision = sum(context_precision_scores) / len(context_precision_scores) if context_precision_scores else None
        avg_context_recall = sum(context_recall_scores) / len(context_recall_scores) if context_recall_scores else None

        # Calculate token statistics
        total_tokens = db.query(func.sum(EvaluationRun.total_tokens)).filter(
            EvaluationRun.status == "completed"
        ).scalar() or 0

        avg_tokens = db.query(func.avg(EvaluationRun.average_tokens_per_query)).filter(
            EvaluationRun.status == "completed"
        ).scalar() or 0

        return MetricsSummaryResponse(
            latest_run_id=str(latest_run.run_id) if latest_run else None,
            latest_run_date=latest_run.completed_at if latest_run else None,
            total_evaluations=total_evaluations,
            successful_evaluations=successful_evaluations,
            success_rate=success_rate,
            latest_faithfulness=safe_float(latest_run.average_faithfulness) if latest_run else None,
            latest_answer_relevance=safe_float(latest_run.average_answer_relevance) if latest_run else None,
            latest_context_precision=safe_float(latest_run.average_context_precision) if latest_run else None,
            latest_context_recall=safe_float(latest_run.average_context_recall) if latest_run else None,
            avg_faithfulness=safe_float(avg_faithfulness),
            avg_answer_relevance=safe_float(avg_answer_relevance),
            avg_context_precision=safe_float(avg_context_precision),
            avg_context_recall=safe_float(avg_context_recall),
            avg_response_time_ms=safe_float(avg_response_time),
            total_tokens=int(total_tokens) if total_tokens else 0,
            avg_tokens_per_query=float(avg_tokens) if avg_tokens else 0.0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics summary: {str(e)}")


@router.get("/trends", response_model=MetricsTrendsResponse)
async def get_metrics_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get historical trends for evaluation metrics

    - **days**: Number of days to look back (1-365)
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        runs = db.query(EvaluationRun).filter(
            EvaluationRun.status == "completed",
            EvaluationRun.completed_at >= cutoff_date
        ).order_by(EvaluationRun.completed_at).all()

        data_points = []
        for run in runs:
            success_rate = None
            if run.total_queries and run.successful_queries:
                success_rate = (run.successful_queries / run.total_queries) * 100

            data_points.append(TrendDataPoint(
                date=run.completed_at,
                run_id=str(run.run_id),
                faithfulness=safe_float(run.average_faithfulness),
                answer_relevance=safe_float(run.average_answer_relevance),
                context_precision=safe_float(run.average_context_precision),
                context_recall=safe_float(run.average_context_recall),
                total_queries=run.total_queries,
                successful_queries=run.successful_queries,
                success_rate=success_rate
            ))

        return MetricsTrendsResponse(
            period_days=days,
            data_points=data_points
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics trends: {str(e)}")


@router.get("/detailed/{run_id}", response_model=DetailedMetricsResponse)
async def get_detailed_metrics(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed metrics for a specific evaluation run

    - **run_id**: UUID of the evaluation run
    """
    try:
        import uuid

        eval_db = EvaluationDB(db)
        run_uuid = uuid.UUID(run_id)

        # Get the run
        run = eval_db.get_evaluation_run(run_uuid)
        if not run:
            raise HTTPException(status_code=404, detail="Evaluation run not found")

        # Get results for this run
        results = eval_db.get_evaluation_results(run_uuid)

        # Calculate detailed metrics
        successful_results = [r for r in results if r.evaluation_status == "success"]
        failed_results = [r for r in results if r.evaluation_status == "error"]

        # Performance metrics
        response_times = [r.response_time_ms for r in successful_results if r.response_time_ms]
        token_counts = [r.token_count for r in successful_results if r.token_count]

        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        total_tokens = sum(token_counts) if token_counts else None
        avg_tokens = sum(token_counts) / len(token_counts) if token_counts else None

        # Status breakdown
        status_breakdown = {}
        for result in results:
            status = result.evaluation_status or "unknown"
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        success_rate = (len(successful_results) / len(results) * 100) if results else 0

        return DetailedMetricsResponse(
            run_id=str(run.run_id),
            run_date=run.completed_at or run.started_at,
            total_queries=len(results),
            successful_queries=len(successful_results),
            failed_queries=len(failed_results),
            success_rate=success_rate,
            faithfulness=float(run.average_faithfulness) if run.average_faithfulness else None,
            answer_relevance=float(run.average_answer_relevance) if run.average_answer_relevance else None,
            context_precision=float(run.average_context_precision) if run.average_context_precision else None,
            context_recall=float(run.average_context_recall) if run.average_context_recall else None,
            avg_response_time_ms=avg_response_time,
            total_tokens=total_tokens,
            avg_tokens_per_query=avg_tokens,
            query_status_breakdown=status_breakdown
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get detailed metrics: {str(e)}")


@router.get("/comparison")
async def compare_runs(
    run_ids: str = Query(..., description="Comma-separated list of run IDs to compare"),
    db: Session = Depends(get_db)
):
    """
    Compare metrics across multiple evaluation runs

    - **run_ids**: Comma-separated list of run UUIDs
    """
    try:
        import uuid

        run_id_list = [run_id.strip() for run_id in run_ids.split(",")]
        if len(run_id_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 runs can be compared at once")

        eval_db = EvaluationDB(db)
        comparison_data = []

        for run_id_str in run_id_list:
            try:
                run_uuid = uuid.UUID(run_id_str)
                run = eval_db.get_evaluation_run(run_uuid)

                if run:
                    success_rate = None
                    if run.total_queries and run.successful_queries:
                        success_rate = (run.successful_queries / run.total_queries) * 100

                    comparison_data.append({
                        "run_id": str(run.run_id),
                        "run_type": run.run_type,
                        "date": run.completed_at or run.started_at,
                        "status": run.status,
                        "total_queries": run.total_queries,
                        "successful_queries": run.successful_queries,
                        "success_rate": success_rate,
                        "faithfulness": float(run.average_faithfulness) if run.average_faithfulness else None,
                        "answer_relevance": float(run.average_answer_relevance) if run.average_answer_relevance else None,
                        "context_precision": float(run.average_context_precision) if run.average_context_precision else None,
                        "context_recall": float(run.average_context_recall) if run.average_context_recall else None
                    })
                else:
                    comparison_data.append({
                        "run_id": run_id_str,
                        "error": "Run not found"
                    })
            except ValueError:
                comparison_data.append({
                    "run_id": run_id_str,
                    "error": "Invalid UUID format"
                })

        return {
            "comparison": comparison_data,
            "total_runs": len(comparison_data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare runs: {str(e)}")


# ==================== Agent 1 Metrics Endpoints ====================

class Agent1MetricsSummaryResponse(BaseModel):
    latest_run_id: Optional[str]
    latest_run_date: Optional[datetime]
    total_evaluations: int
    successful_evaluations: int
    success_rate: float

    # Latest deterministic metrics
    latest_merchant_match: Optional[float]
    latest_date_match: Optional[float]
    latest_amount_match: Optional[float]
    latest_item_f1: Optional[float]

    # Latest LLM-as-Judge metrics
    latest_merchant_similarity: Optional[float]
    latest_items_similarity: Optional[float]
    latest_overall_quality: Optional[float]

    # Overall averages
    avg_merchant_match: Optional[float]
    avg_date_match: Optional[float]
    avg_amount_match: Optional[float]
    avg_item_precision: Optional[float]
    avg_item_recall: Optional[float]
    avg_item_f1: Optional[float]
    avg_merchant_similarity: Optional[float]
    avg_items_similarity: Optional[float]
    avg_overall_quality: Optional[float]
    avg_processing_time_ms: Optional[float]

    # Token consumption metrics
    total_tokens_used: Optional[int] = 0
    avg_tokens_per_evaluation: Optional[float] = 0


class Agent1TrendDataPoint(BaseModel):
    date: datetime
    run_id: str

    # Deterministic metrics
    merchant_match: Optional[float]
    date_match: Optional[float]
    amount_match: Optional[float]
    item_f1: Optional[float]

    # LLM metrics
    merchant_similarity: Optional[float]
    items_similarity: Optional[float]
    overall_quality: Optional[float]

    total_tickets: Optional[int]
    successful_tickets: Optional[int]
    success_rate: Optional[float]


class Agent1MetricsTrendsResponse(BaseModel):
    period_days: int
    data_points: List[Agent1TrendDataPoint]


@router.get("/agent1/summary", response_model=Agent1MetricsSummaryResponse)
async def get_agent1_metrics_summary(db: Session = Depends(get_db)):
    """
    Get summary of latest Agent 1 (OCR/Formatter) evaluation metrics
    """
    try:
        eval_db = EvaluationDB(db)

        # Get latest completed run
        latest_run = eval_db.get_agent1_latest_metrics()

        # Get overall statistics
        completed_runs = db.query(Agent1EvaluationRun).filter(
            Agent1EvaluationRun.status == "completed"
        ).all()

        total_evaluations = 0
        successful_evaluations = 0

        # Collect scores for averaging
        merchant_match_scores = []
        date_match_scores = []
        amount_match_scores = []
        item_precision_scores = []
        item_recall_scores = []
        item_f1_scores = []
        merchant_similarity_scores = []
        items_similarity_scores = []
        overall_quality_scores = []
        processing_times = []

        for run in completed_runs:
            if run.total_tickets:
                total_evaluations += run.total_tickets
            if run.successful_tickets:
                successful_evaluations += run.successful_tickets

            # Collect metric scores
            if safe_float(run.average_merchant_match) is not None:
                merchant_match_scores.append(safe_float(run.average_merchant_match))
            if safe_float(run.average_date_match) is not None:
                date_match_scores.append(safe_float(run.average_date_match))
            if safe_float(run.average_amount_match) is not None:
                amount_match_scores.append(safe_float(run.average_amount_match))
            if safe_float(run.average_item_precision) is not None:
                item_precision_scores.append(safe_float(run.average_item_precision))
            if safe_float(run.average_item_recall) is not None:
                item_recall_scores.append(safe_float(run.average_item_recall))
            if safe_float(run.average_item_f1) is not None:
                item_f1_scores.append(safe_float(run.average_item_f1))
            if safe_float(run.average_merchant_similarity) is not None:
                merchant_similarity_scores.append(safe_float(run.average_merchant_similarity))
            if safe_float(run.average_items_similarity) is not None:
                items_similarity_scores.append(safe_float(run.average_items_similarity))
            if safe_float(run.average_overall_quality) is not None:
                overall_quality_scores.append(safe_float(run.average_overall_quality))

        # Get average processing times from results
        avg_processing_time = db.query(func.avg(Agent1EvaluationResult.processing_time_ms)).filter(
            Agent1EvaluationResult.evaluation_status == "success"
        ).scalar()

        success_rate = (successful_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0

        # Calculate overall averages
        def avg_or_none(scores):
            return sum(scores) / len(scores) if scores else None

        # Calculate token statistics
        total_tokens = db.query(func.sum(Agent1EvaluationRun.total_tokens)).filter(
            Agent1EvaluationRun.status == "completed"
        ).scalar() or 0

        avg_tokens = db.query(func.avg(Agent1EvaluationRun.average_tokens_per_ticket)).filter(
            Agent1EvaluationRun.status == "completed"
        ).scalar() or 0

        return Agent1MetricsSummaryResponse(
            latest_run_id=str(latest_run.run_id) if latest_run else None,
            latest_run_date=latest_run.completed_at if latest_run else None,
            total_evaluations=total_evaluations,
            successful_evaluations=successful_evaluations,
            success_rate=success_rate,
            latest_merchant_match=safe_float(latest_run.average_merchant_match) if latest_run else None,
            latest_date_match=safe_float(latest_run.average_date_match) if latest_run else None,
            latest_amount_match=safe_float(latest_run.average_amount_match) if latest_run else None,
            latest_item_f1=safe_float(latest_run.average_item_f1) if latest_run else None,
            latest_merchant_similarity=safe_float(latest_run.average_merchant_similarity) if latest_run else None,
            latest_items_similarity=safe_float(latest_run.average_items_similarity) if latest_run else None,
            latest_overall_quality=safe_float(latest_run.average_overall_quality) if latest_run else None,
            avg_merchant_match=safe_float(avg_or_none(merchant_match_scores)),
            avg_date_match=safe_float(avg_or_none(date_match_scores)),
            avg_amount_match=safe_float(avg_or_none(amount_match_scores)),
            avg_item_precision=safe_float(avg_or_none(item_precision_scores)),
            avg_item_recall=safe_float(avg_or_none(item_recall_scores)),
            avg_item_f1=safe_float(avg_or_none(item_f1_scores)),
            avg_merchant_similarity=safe_float(avg_or_none(merchant_similarity_scores)),
            avg_items_similarity=safe_float(avg_or_none(items_similarity_scores)),
            avg_overall_quality=safe_float(avg_or_none(overall_quality_scores)),
            avg_processing_time_ms=safe_float(avg_processing_time),
            total_tokens_used=int(total_tokens) if total_tokens else 0,
            avg_tokens_per_evaluation=float(avg_tokens) if avg_tokens else 0.0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Agent 1 metrics summary: {str(e)}")


@router.get("/agent1/trends", response_model=Agent1MetricsTrendsResponse)
async def get_agent1_metrics_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get historical trends for Agent 1 evaluation metrics

    - **days**: Number of days to look back (1-365)
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        runs = db.query(Agent1EvaluationRun).filter(
            Agent1EvaluationRun.status == "completed",
            Agent1EvaluationRun.completed_at >= cutoff_date
        ).order_by(Agent1EvaluationRun.completed_at).all()

        data_points = []
        for run in runs:
            success_rate = None
            if run.total_tickets and run.successful_tickets:
                success_rate = (run.successful_tickets / run.total_tickets) * 100

            data_points.append(Agent1TrendDataPoint(
                date=run.completed_at,
                run_id=str(run.run_id),
                merchant_match=safe_float(run.average_merchant_match),
                date_match=safe_float(run.average_date_match),
                amount_match=safe_float(run.average_amount_match),
                item_f1=safe_float(run.average_item_f1),
                merchant_similarity=safe_float(run.average_merchant_similarity),
                items_similarity=safe_float(run.average_items_similarity),
                overall_quality=safe_float(run.average_overall_quality),
                total_tickets=run.total_tickets,
                successful_tickets=run.successful_tickets,
                success_rate=success_rate
            ))

        return Agent1MetricsTrendsResponse(
            period_days=days,
            data_points=data_points
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Agent 1 metrics trends: {str(e)}")


@router.get("/agent1/runs")
async def get_agent1_runs(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent Agent 1 evaluation runs

    - **limit**: Maximum number of runs to return (1-100)
    """
    try:
        runs = db.query(Agent1EvaluationRun).order_by(
            desc(Agent1EvaluationRun.started_at)
        ).limit(limit).all()

        runs_data = []
        for run in runs:
            runs_data.append({
                "run_id": str(run.run_id),
                "run_type": run.run_type,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "total_tickets": run.total_tickets,
                "successful_tickets": run.successful_tickets,
                "average_merchant_match": safe_float(run.average_merchant_match),
                "average_date_match": safe_float(run.average_date_match),
                "average_amount_match": safe_float(run.average_amount_match),
                "average_item_precision": safe_float(run.average_item_precision),
                "average_item_recall": safe_float(run.average_item_recall),
                "average_item_f1": safe_float(run.average_item_f1),
                "average_merchant_similarity": safe_float(run.average_merchant_similarity),
                "average_items_similarity": safe_float(run.average_items_similarity),
                "average_overall_quality": safe_float(run.average_overall_quality),
                "run_metadata": run.run_metadata
            })

        return runs_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Agent 1 runs: {str(e)}")


# ==================== Agent 2 Operational Metrics Endpoints ====================

class Agent2OperationalMetrics(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    total_tokens: int
    avg_tokens_per_query: float
    total_response_time_ms: int
    avg_response_time_ms: float
    estimated_cost: float


@router.get("/agent2/operational", response_model=Agent2OperationalMetrics)
async def get_agent2_operational_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get operational metrics for Agent 2 from actual query logs

    - **days**: Number of days to look back (1-365)
    """
    try:
        from sqlalchemy import text
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query agent2_query_logs table
        query = text("""
            SELECT
                COUNT(*) as total_queries,
                COUNT(*) FILTER (WHERE success = true) as successful_queries,
                COUNT(*) FILTER (WHERE success = false) as failed_queries,
                COALESCE(SUM(token_count), 0) as total_tokens,
                COALESCE(AVG(token_count), 0) as avg_tokens,
                COALESCE(SUM(response_time_ms), 0) as total_response_ms,
                COALESCE(AVG(response_time_ms), 0) as avg_response_ms
            FROM agent2_query_logs
            WHERE created_at >= :cutoff_date
        """)

        result = db.execute(query, {"cutoff_date": cutoff_date}).fetchone()

        total_queries = result[0] or 0
        successful_queries = result[1] or 0
        failed_queries = result[2] or 0
        total_tokens = result[3] or 0
        avg_tokens = result[4] or 0
        total_response_ms = result[5] or 0
        avg_response_ms = result[6] or 0

        # Estimate cost (GPT-4o pricing: ~$2.50/1M input, ~$10/1M output)
        # Using conservative average of $6/1M tokens
        estimated_cost = (total_tokens / 1_000_000) * 6.0

        return Agent2OperationalMetrics(
            total_queries=total_queries,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            total_tokens=total_tokens,
            avg_tokens_per_query=float(avg_tokens),
            total_response_time_ms=total_response_ms,
            avg_response_time_ms=float(avg_response_ms),
            estimated_cost=estimated_cost
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Agent 2 operational metrics: {str(e)}")