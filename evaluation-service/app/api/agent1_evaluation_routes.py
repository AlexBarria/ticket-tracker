"""
Agent 1 (OCR/Formatter) Evaluation API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
import logging

from ..database import get_db, EvaluationDB, Agent1EvaluationRun, Agent1EvaluationResult
from ..evaluators.agent1_evaluator import Agent1Evaluator
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class Agent1RealtimeEvaluationRequest(BaseModel):
    ticket_id: int
    expected_merchant: str
    expected_date: str  # Format: YYYY-MM-DD
    expected_amount: float
    expected_items: List[dict]  # List of {"description": str, "price": float}


class Agent1EvaluationRunResponse(BaseModel):
    run_id: str
    run_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_tickets: Optional[int]
    successful_tickets: Optional[int]

    # Deterministic metrics
    average_merchant_match: Optional[float]
    average_date_match: Optional[float]
    average_amount_match: Optional[float]
    average_item_precision: Optional[float]
    average_item_recall: Optional[float]
    average_item_f1: Optional[float]

    # LLM-as-Judge metrics
    average_merchant_similarity: Optional[float]
    average_items_similarity: Optional[float]
    average_overall_quality: Optional[float]

    class Config:
        from_attributes = True


class Agent1EvaluationResultResponse(BaseModel):
    id: int
    test_id: Optional[str]
    filename: Optional[str]

    # Expected vs Actual
    expected_merchant: Optional[str]
    actual_merchant: Optional[str]
    expected_amount: Optional[float]
    actual_amount: Optional[float]

    # Deterministic metrics
    merchant_exact_match: Optional[bool]
    date_exact_match: Optional[bool]
    amount_exact_match: Optional[bool]
    item_precision: Optional[float]
    item_recall: Optional[float]
    item_f1: Optional[float]

    # LLM metrics
    merchant_similarity_score: Optional[float]
    items_similarity_score: Optional[float]
    overall_quality_score: Optional[float]
    llm_feedback: Optional[str]

    processing_time_ms: Optional[int]
    evaluation_status: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class TriggerResponse(BaseModel):
    message: str
    run_id: Optional[str] = None
    status: str


@router.post("/realtime")
async def evaluate_agent1_realtime(request: Agent1RealtimeEvaluationRequest):
    """
    Evaluate a single Agent 1 (OCR) ticket in real-time

    - **ticket_id**: ID of the ticket in the database (already processed by Agent 1)
    - **expected_merchant**: Correct merchant name
    - **expected_date**: Correct transaction date (YYYY-MM-DD)
    - **expected_amount**: Correct total amount
    - **expected_items**: List of correct items with description and price
    """
    try:
        evaluator = Agent1Evaluator()
        result = await evaluator.evaluate_realtime_ticket(
            ticket_id=request.ticket_id,
            expected_merchant=request.expected_merchant,
            expected_date=request.expected_date,
            expected_amount=request.expected_amount,
            expected_items=request.expected_items
        )
        return result
    except Exception as e:
        logger.error(f"Real-time Agent 1 evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate ticket: {str(e)}")


@router.get("/runs", response_model=List[Agent1EvaluationRunResponse])
async def list_agent1_evaluation_runs(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List recent Agent 1 evaluation runs

    - **limit**: Maximum number of runs to return (1-100)
    """
    try:
        eval_db = EvaluationDB(db)
        runs = eval_db.get_agent1_evaluation_runs(limit=limit)

        def safe_float(value):
            """Convert NaN values to None for JSON serialization"""
            import math
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return None
            return value

        return [
            Agent1EvaluationRunResponse(
                run_id=str(run.run_id),
                run_type=run.run_type,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                total_tickets=run.total_tickets,
                successful_tickets=run.successful_tickets,
                average_merchant_match=safe_float(run.average_merchant_match),
                average_date_match=safe_float(run.average_date_match),
                average_amount_match=safe_float(run.average_amount_match),
                average_item_precision=safe_float(run.average_item_precision),
                average_item_recall=safe_float(run.average_item_recall),
                average_item_f1=safe_float(run.average_item_f1),
                average_merchant_similarity=safe_float(run.average_merchant_similarity),
                average_items_similarity=safe_float(run.average_items_similarity),
                average_overall_quality=safe_float(run.average_overall_quality)
            )
            for run in runs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Agent 1 runs: {str(e)}")


@router.get("/runs/{run_id}", response_model=Agent1EvaluationRunResponse)
async def get_agent1_evaluation_run(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific Agent 1 evaluation run

    - **run_id**: UUID of the evaluation run
    """
    try:
        eval_db = EvaluationDB(db)
        run_uuid = uuid.UUID(run_id)
        run = eval_db.get_agent1_evaluation_run(run_uuid)

        if not run:
            raise HTTPException(status_code=404, detail="Agent 1 evaluation run not found")

        return Agent1EvaluationRunResponse(
            run_id=str(run.run_id),
            run_type=run.run_type,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_tickets=run.total_tickets,
            successful_tickets=run.successful_tickets,
            average_merchant_match=float(run.average_merchant_match) if run.average_merchant_match else None,
            average_date_match=float(run.average_date_match) if run.average_date_match else None,
            average_amount_match=float(run.average_amount_match) if run.average_amount_match else None,
            average_item_precision=float(run.average_item_precision) if run.average_item_precision else None,
            average_item_recall=float(run.average_item_recall) if run.average_item_recall else None,
            average_item_f1=float(run.average_item_f1) if run.average_item_f1 else None,
            average_merchant_similarity=float(run.average_merchant_similarity) if run.average_merchant_similarity else None,
            average_items_similarity=float(run.average_items_similarity) if run.average_items_similarity else None,
            average_overall_quality=float(run.average_overall_quality) if run.average_overall_quality else None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Agent 1 run: {str(e)}")


@router.get("/runs/{run_id}/results", response_model=List[Agent1EvaluationResultResponse])
async def get_agent1_evaluation_results(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed results for a specific Agent 1 evaluation run

    - **run_id**: UUID of the evaluation run
    """
    try:
        eval_db = EvaluationDB(db)
        run_uuid = uuid.UUID(run_id)

        # Check if run exists
        run = eval_db.get_agent1_evaluation_run(run_uuid)
        if not run:
            raise HTTPException(status_code=404, detail="Agent 1 evaluation run not found")

        # Get results
        results = eval_db.get_agent1_evaluation_results(run_uuid)

        return [
            Agent1EvaluationResultResponse(
                id=result.id,
                test_id=result.test_id,
                filename=result.filename,
                expected_merchant=result.expected_merchant,
                actual_merchant=result.actual_merchant,
                expected_amount=float(result.expected_amount) if result.expected_amount else None,
                actual_amount=float(result.actual_amount) if result.actual_amount else None,
                merchant_exact_match=result.merchant_exact_match,
                date_exact_match=result.date_exact_match,
                amount_exact_match=result.amount_exact_match,
                item_precision=float(result.item_precision) if result.item_precision else None,
                item_recall=float(result.item_recall) if result.item_recall else None,
                item_f1=float(result.item_f1) if result.item_f1 else None,
                merchant_similarity_score=float(result.merchant_similarity_score) if result.merchant_similarity_score else None,
                items_similarity_score=float(result.items_similarity_score) if result.items_similarity_score else None,
                overall_quality_score=float(result.overall_quality_score) if result.overall_quality_score else None,
                llm_feedback=result.llm_feedback,
                processing_time_ms=result.processing_time_ms,
                evaluation_status=result.evaluation_status,
                error_message=result.error_message
            )
            for result in results
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Agent 1 results: {str(e)}")
