from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging

from ..database import get_db, EvaluationDB, EvaluationRun, EvaluationResult
from ..scheduler import trigger_manual_evaluation, trigger_sample_evaluation, get_scheduler_status
from ..evaluators.ragas_evaluator import RAGASEvaluator
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class EvaluationRunRequest(BaseModel):
    run_type: str = "manual"
    sample_size: Optional[int] = None


class EvaluationRunResponse(BaseModel):
    run_id: str
    run_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_queries: Optional[int]
    successful_queries: Optional[int]
    average_faithfulness: Optional[float]
    average_answer_relevance: Optional[float]
    average_context_precision: Optional[float]
    average_context_recall: Optional[float]

    class Config:
        from_attributes = True


class EvaluationResultResponse(BaseModel):
    id: int
    query_id: Optional[str]
    query_text: str
    generated_answer: Optional[str]
    retrieved_context: Optional[str]
    reference_answer: Optional[str]
    faithfulness_score: Optional[float]
    answer_relevance_score: Optional[float]
    context_precision_score: Optional[float]
    context_recall_score: Optional[float]
    response_time_ms: Optional[int]
    token_count: Optional[int]
    evaluation_status: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TriggerResponse(BaseModel):
    message: str
    run_id: Optional[str] = None
    status: str


class SchedulerStatusResponse(BaseModel):
    status: str
    next_run: Optional[str]
    jobs: List[dict]


class RealtimeEvaluationRequest(BaseModel):
    question: str
    reference_answer: Optional[str] = ""
    query_id: Optional[str] = None


class RealtimeEvaluationResponse(BaseModel):
    run_id: str
    query_id: str
    status: str
    faithfulness_score: Optional[float]
    answer_relevance_score: Optional[float]
    context_precision_score: Optional[float]
    context_recall_score: Optional[float]
    response_time_ms: Optional[int]
    error_message: Optional[str]


@router.post("/run", response_model=TriggerResponse)
async def trigger_evaluation(
    request: EvaluationRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger a new evaluation run

    - **run_type**: Type of evaluation (manual, sample)
    - **sample_size**: Number of queries for sample evaluation (optional)
    """
    try:
        if request.run_type == "sample":
            sample_size = request.sample_size or 5
            background_tasks.add_task(trigger_sample_evaluation, sample_size)
            return TriggerResponse(
                message=f"Sample evaluation with {sample_size} queries triggered",
                status="started"
            )
        else:
            background_tasks.add_task(trigger_manual_evaluation)
            return TriggerResponse(
                message="Manual evaluation triggered",
                status="started"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger evaluation: {str(e)}")


@router.get("/runs", response_model=List[EvaluationRunResponse])
async def list_evaluation_runs(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List recent evaluation runs

    - **limit**: Maximum number of runs to return (1-100)
    """
    try:
        eval_db = EvaluationDB(db)
        runs = eval_db.get_evaluation_runs(limit=limit)

        def safe_float(value):
            """Convert NaN values to None for JSON serialization"""
            import math
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return None
            return value

        return [
            EvaluationRunResponse(
                run_id=str(run.run_id),
                run_type=run.run_type,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                total_queries=run.total_queries,
                successful_queries=run.successful_queries,
                average_faithfulness=safe_float(run.average_faithfulness),
                average_answer_relevance=safe_float(run.average_answer_relevance),
                average_context_precision=safe_float(run.average_context_precision),
                average_context_recall=safe_float(run.average_context_recall)
            )
            for run in runs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve runs: {str(e)}")


@router.get("/runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific evaluation run

    - **run_id**: UUID of the evaluation run
    """
    try:
        eval_db = EvaluationDB(db)
        run_uuid = uuid.UUID(run_id)
        run = eval_db.get_evaluation_run(run_uuid)

        if not run:
            raise HTTPException(status_code=404, detail="Evaluation run not found")

        return EvaluationRunResponse(
            run_id=str(run.run_id),
            run_type=run.run_type,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_queries=run.total_queries,
            successful_queries=run.successful_queries,
            average_faithfulness=float(run.average_faithfulness) if run.average_faithfulness else None,
            average_answer_relevance=float(run.average_answer_relevance) if run.average_answer_relevance else None,
            average_context_precision=float(run.average_context_precision) if run.average_context_precision else None,
            average_context_recall=float(run.average_context_recall) if run.average_context_recall else None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve run: {str(e)}")


@router.get("/runs/{run_id}/results", response_model=List[EvaluationResultResponse])
async def get_evaluation_results(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed results for a specific evaluation run

    - **run_id**: UUID of the evaluation run
    """
    try:
        eval_db = EvaluationDB(db)
        run_uuid = uuid.UUID(run_id)

        # Check if run exists
        run = eval_db.get_evaluation_run(run_uuid)
        if not run:
            raise HTTPException(status_code=404, detail="Evaluation run not found")

        # Get results
        results = eval_db.get_evaluation_results(run_uuid)

        return [
            EvaluationResultResponse(
                id=result.id,
                query_id=result.query_id,
                query_text=result.query_text,
                generated_answer=result.generated_answer,
                retrieved_context=result.retrieved_context,
                reference_answer=result.reference_answer,
                faithfulness_score=float(result.faithfulness_score) if result.faithfulness_score else None,
                answer_relevance_score=float(result.answer_relevance_score) if result.answer_relevance_score else None,
                context_precision_score=float(result.context_precision_score) if result.context_precision_score else None,
                context_recall_score=float(result.context_recall_score) if result.context_recall_score else None,
                response_time_ms=result.response_time_ms,
                token_count=result.token_count,
                evaluation_status=result.evaluation_status,
                error_message=result.error_message,
                created_at=result.created_at
            )
            for result in results
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status_endpoint():
    """
    Get the current scheduler status and next scheduled run
    """
    try:
        status = get_scheduler_status()
        return SchedulerStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/sample", response_model=TriggerResponse)
async def trigger_sample_evaluation_endpoint(
    background_tasks: BackgroundTasks,
    sample_size: int = Query(5, ge=1, le=10)
):
    """
    Trigger a sample evaluation for testing

    - **sample_size**: Number of queries to evaluate (1-10)
    """
    try:
        background_tasks.add_task(trigger_sample_evaluation, sample_size)
        return TriggerResponse(
            message=f"Sample evaluation with {sample_size} queries triggered",
            status="started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger sample evaluation: {str(e)}")


@router.post("/realtime", response_model=RealtimeEvaluationResponse)
async def evaluate_realtime_query_endpoint(
    request: RealtimeEvaluationRequest,
    background_tasks: BackgroundTasks
):
    """
    Evaluate a single query in real-time (e.g., from admin dashboard)

    - **question**: The question to evaluate
    - **reference_answer**: Optional ground truth answer for comparison
    - **query_id**: Optional custom query ID
    """
    try:
        evaluator = RAGASEvaluator()

        # Run evaluation in background
        result = await evaluator.evaluate_realtime_query(
            question=request.question,
            reference_answer=request.reference_answer or "",
            query_id=request.query_id
        )

        return RealtimeEvaluationResponse(**result)
    except Exception as e:
        logger.error(f"Real-time evaluation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate query: {str(e)}")