from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from typing import Optional, List
import uuid
import json

from .config import settings

# SQLAlchemy setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    run_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_queries = Column(Integer, nullable=True)
    successful_queries = Column(Integer, nullable=True)
    average_faithfulness = Column(Numeric(5, 4), nullable=True)
    average_answer_relevance = Column(Numeric(5, 4), nullable=True)
    average_context_precision = Column(Numeric(5, 4), nullable=True)
    average_context_recall = Column(Numeric(5, 4), nullable=True)
    total_tokens = Column(Integer, default=0)
    average_tokens_per_query = Column(Numeric(10, 2), default=0)
    run_metadata = Column(JSONB, nullable=True)

    # Relationship
    results = relationship("EvaluationResult", back_populates="run")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_runs.run_id"), nullable=False)
    query_id = Column(String(20), nullable=True)
    query_text = Column(Text, nullable=False)
    generated_answer = Column(Text, nullable=True)
    retrieved_context = Column(Text, nullable=True)
    reference_answer = Column(Text, nullable=True)

    # RAGAS metrics
    faithfulness_score = Column(Numeric(5, 4), nullable=True)
    answer_relevance_score = Column(Numeric(5, 4), nullable=True)
    context_precision_score = Column(Numeric(5, 4), nullable=True)
    context_recall_score = Column(Numeric(5, 4), nullable=True)

    response_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    evaluation_status = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    run = relationship("EvaluationRun", back_populates="results")


# Agent 1 Evaluation Models
class Agent1EvaluationRun(Base):
    __tablename__ = "agent1_evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    run_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_tickets = Column(Integer, nullable=True)
    successful_tickets = Column(Integer, nullable=True)

    # Deterministic metrics
    average_merchant_match = Column(Numeric(5, 4), nullable=True)
    average_date_match = Column(Numeric(5, 4), nullable=True)
    average_amount_match = Column(Numeric(5, 4), nullable=True)
    average_item_precision = Column(Numeric(5, 4), nullable=True)
    average_item_recall = Column(Numeric(5, 4), nullable=True)
    average_item_f1 = Column(Numeric(5, 4), nullable=True)

    # LLM-as-Judge metrics
    average_merchant_similarity = Column(Numeric(5, 4), nullable=True)
    average_items_similarity = Column(Numeric(5, 4), nullable=True)
    average_overall_quality = Column(Numeric(5, 4), nullable=True)

    # Token consumption metrics
    total_tokens = Column(Integer, default=0)
    average_tokens_per_ticket = Column(Numeric(10, 2), default=0)

    run_metadata = Column(JSONB, nullable=True)

    # Relationship
    results = relationship("Agent1EvaluationResult", back_populates="run")


class Agent1EvaluationResult(Base):
    __tablename__ = "agent1_evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent1_evaluation_runs.run_id"), nullable=False)
    test_id = Column(String(50), nullable=True)
    filename = Column(String(255), nullable=True)

    # Ground truth data
    expected_merchant = Column(String(255), nullable=True)
    expected_date = Column(Date, nullable=True)
    expected_amount = Column(Numeric(10, 2), nullable=True)
    expected_items = Column(JSONB, nullable=True)

    # Agent 1 output
    actual_merchant = Column(String(255), nullable=True)
    actual_date = Column(Date, nullable=True)
    actual_amount = Column(Numeric(10, 2), nullable=True)
    actual_items = Column(JSONB, nullable=True)

    # Deterministic metrics
    merchant_exact_match = Column(Boolean, nullable=True)
    date_exact_match = Column(Boolean, nullable=True)
    amount_exact_match = Column(Boolean, nullable=True)
    item_precision = Column(Numeric(5, 4), nullable=True)
    item_recall = Column(Numeric(5, 4), nullable=True)
    item_f1 = Column(Numeric(5, 4), nullable=True)

    # LLM-as-Judge metrics
    merchant_similarity_score = Column(Numeric(5, 4), nullable=True)
    items_similarity_score = Column(Numeric(5, 4), nullable=True)
    overall_quality_score = Column(Numeric(5, 4), nullable=True)
    llm_feedback = Column(Text, nullable=True)

    processing_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, default=0)
    evaluation_status = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    run = relationship("Agent1EvaluationRun", back_populates="results")


# Database dependency
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database operations
class EvaluationDB:
    def __init__(self, db: Session):
        self.db = db

    def create_evaluation_run(self, run_type: str, status: str = "running") -> EvaluationRun:
        db_run = EvaluationRun(
            run_type=run_type,
            status=status
        )
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def update_evaluation_run(
        self,
        run_id: uuid.UUID,
        status: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        total_queries: Optional[int] = None,
        successful_queries: Optional[int] = None,
        average_faithfulness: Optional[float] = None,
        average_answer_relevance: Optional[float] = None,
        average_context_precision: Optional[float] = None,
        average_context_recall: Optional[float] = None,
        total_tokens: Optional[int] = None,
        average_tokens_per_query: Optional[float] = None,
        run_metadata: Optional[dict] = None
    ) -> Optional[EvaluationRun]:
        db_run = self.db.query(EvaluationRun).filter(EvaluationRun.run_id == run_id).first()
        if not db_run:
            return None

        if status is not None:
            db_run.status = status
        if completed_at is not None:
            db_run.completed_at = completed_at
        if total_queries is not None:
            db_run.total_queries = total_queries
        if successful_queries is not None:
            db_run.successful_queries = successful_queries
        if average_faithfulness is not None:
            db_run.average_faithfulness = average_faithfulness
        if average_answer_relevance is not None:
            db_run.average_answer_relevance = average_answer_relevance
        if average_context_precision is not None:
            db_run.average_context_precision = average_context_precision
        if average_context_recall is not None:
            db_run.average_context_recall = average_context_recall
        if total_tokens is not None:
            db_run.total_tokens = total_tokens
        if average_tokens_per_query is not None:
            db_run.average_tokens_per_query = average_tokens_per_query
        if run_metadata is not None:
            db_run.run_metadata = run_metadata

        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def create_evaluation_result(
        self,
        run_id: uuid.UUID,
        query_id: Optional[str],
        query_text: str,
        generated_answer: Optional[str] = None,
        retrieved_context: Optional[str] = None,
        reference_answer: Optional[str] = None,
        faithfulness_score: Optional[float] = None,
        answer_relevance_score: Optional[float] = None,
        context_precision_score: Optional[float] = None,
        context_recall_score: Optional[float] = None,
        response_time_ms: Optional[int] = None,
        token_count: Optional[int] = None,
        evaluation_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> EvaluationResult:
        db_result = EvaluationResult(
            run_id=run_id,
            query_id=query_id,
            query_text=query_text,
            generated_answer=generated_answer,
            retrieved_context=retrieved_context,
            reference_answer=reference_answer,
            faithfulness_score=faithfulness_score,
            answer_relevance_score=answer_relevance_score,
            context_precision_score=context_precision_score,
            context_recall_score=context_recall_score,
            response_time_ms=response_time_ms,
            token_count=token_count,
            evaluation_status=evaluation_status,
            error_message=error_message
        )
        self.db.add(db_result)
        self.db.commit()
        self.db.refresh(db_result)
        return db_result

    def get_evaluation_runs(self, limit: int = 50) -> List[EvaluationRun]:
        return self.db.query(EvaluationRun).order_by(EvaluationRun.started_at.desc()).limit(limit).all()

    def get_evaluation_run(self, run_id: uuid.UUID) -> Optional[EvaluationRun]:
        return self.db.query(EvaluationRun).filter(EvaluationRun.run_id == run_id).first()

    def get_evaluation_results(self, run_id: uuid.UUID) -> List[EvaluationResult]:
        return self.db.query(EvaluationResult).filter(EvaluationResult.run_id == run_id).all()

    def get_latest_metrics(self) -> Optional[EvaluationRun]:
        return self.db.query(EvaluationRun).filter(EvaluationRun.status == "completed").order_by(EvaluationRun.completed_at.desc()).first()

    # ==================== Agent 1 Evaluation Methods ====================

    def create_agent1_evaluation_run(self, run_type: str, status: str = "running") -> Agent1EvaluationRun:
        db_run = Agent1EvaluationRun(
            run_type=run_type,
            status=status
        )
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def update_agent1_evaluation_run(
        self,
        run_id: uuid.UUID,
        status: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        total_tickets: Optional[int] = None,
        successful_tickets: Optional[int] = None,
        average_merchant_match: Optional[float] = None,
        average_date_match: Optional[float] = None,
        average_amount_match: Optional[float] = None,
        average_item_precision: Optional[float] = None,
        average_item_recall: Optional[float] = None,
        average_item_f1: Optional[float] = None,
        average_merchant_similarity: Optional[float] = None,
        average_items_similarity: Optional[float] = None,
        average_overall_quality: Optional[float] = None,
        total_tokens: Optional[int] = None,
        average_tokens_per_ticket: Optional[float] = None,
        run_metadata: Optional[dict] = None
    ) -> Optional[Agent1EvaluationRun]:
        db_run = self.db.query(Agent1EvaluationRun).filter(Agent1EvaluationRun.run_id == run_id).first()
        if not db_run:
            return None

        if status is not None:
            db_run.status = status
        if completed_at is not None:
            db_run.completed_at = completed_at
        if total_tickets is not None:
            db_run.total_tickets = total_tickets
        if successful_tickets is not None:
            db_run.successful_tickets = successful_tickets
        if average_merchant_match is not None:
            db_run.average_merchant_match = average_merchant_match
        if average_date_match is not None:
            db_run.average_date_match = average_date_match
        if average_amount_match is not None:
            db_run.average_amount_match = average_amount_match
        if average_item_precision is not None:
            db_run.average_item_precision = average_item_precision
        if average_item_recall is not None:
            db_run.average_item_recall = average_item_recall
        if average_item_f1 is not None:
            db_run.average_item_f1 = average_item_f1
        if average_merchant_similarity is not None:
            db_run.average_merchant_similarity = average_merchant_similarity
        if average_items_similarity is not None:
            db_run.average_items_similarity = average_items_similarity
        if average_overall_quality is not None:
            db_run.average_overall_quality = average_overall_quality
        if total_tokens is not None:
            db_run.total_tokens = total_tokens
        if average_tokens_per_ticket is not None:
            db_run.average_tokens_per_ticket = average_tokens_per_ticket
        if run_metadata is not None:
            db_run.run_metadata = run_metadata

        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def create_agent1_evaluation_result(
        self,
        run_id: uuid.UUID,
        result_data: dict
    ) -> Agent1EvaluationResult:
        """Create an Agent 1 evaluation result from a result dictionary"""

        # Parse expected and actual data
        expected = result_data.get("expected", {})
        actual = result_data.get("actual", {})

        # Convert date strings to date objects
        expected_date = None
        if expected.get("transaction_date"):
            try:
                from datetime import datetime as dt
                expected_date = dt.strptime(expected["transaction_date"], "%Y-%m-%d").date()
            except:
                pass

        actual_date = None
        if actual.get("transaction_date"):
            try:
                from datetime import datetime as dt
                actual_date = dt.strptime(actual["transaction_date"], "%Y-%m-%d").date()
            except:
                pass

        # Helper to convert empty strings to None for numeric fields
        def safe_numeric(value):
            if value == "" or value is None:
                return None
            try:
                return float(value) if value else None
            except (ValueError, TypeError):
                return None

        db_result = Agent1EvaluationResult(
            run_id=run_id,
            test_id=result_data.get("test_id"),
            filename=result_data.get("filename"),

            # Expected data
            expected_merchant=expected.get("merchant_name") or None,
            expected_date=expected_date,
            expected_amount=safe_numeric(expected.get("total_amount")),
            expected_items=expected.get("items"),

            # Actual data
            actual_merchant=actual.get("merchant_name") or None,
            actual_date=actual_date,
            actual_amount=safe_numeric(actual.get("total_amount")),
            actual_items=actual.get("items"),

            # Deterministic metrics
            merchant_exact_match=result_data.get("merchant_match"),
            date_exact_match=result_data.get("date_match"),
            amount_exact_match=result_data.get("amount_match"),
            item_precision=result_data.get("item_precision"),
            item_recall=result_data.get("item_recall"),
            item_f1=result_data.get("item_f1"),

            # LLM-as-Judge metrics
            merchant_similarity_score=result_data.get("merchant_similarity"),
            items_similarity_score=result_data.get("items_similarity"),
            overall_quality_score=result_data.get("overall_quality"),
            llm_feedback=result_data.get("llm_feedback"),

            processing_time_ms=result_data.get("processing_time_ms"),
            evaluation_status=result_data.get("evaluation_status"),
            error_message=result_data.get("error_message")
        )

        self.db.add(db_result)
        self.db.commit()
        self.db.refresh(db_result)
        return db_result

    def get_agent1_evaluation_runs(self, limit: int = 50) -> List[Agent1EvaluationRun]:
        return self.db.query(Agent1EvaluationRun).order_by(Agent1EvaluationRun.started_at.desc()).limit(limit).all()

    def get_agent1_evaluation_run(self, run_id: uuid.UUID) -> Optional[Agent1EvaluationRun]:
        return self.db.query(Agent1EvaluationRun).filter(Agent1EvaluationRun.run_id == run_id).first()

    def get_agent1_evaluation_results(self, run_id: uuid.UUID) -> List[Agent1EvaluationResult]:
        return self.db.query(Agent1EvaluationResult).filter(Agent1EvaluationResult.run_id == run_id).all()

    def get_agent1_latest_metrics(self) -> Optional[Agent1EvaluationRun]:
        return self.db.query(Agent1EvaluationRun).filter(Agent1EvaluationRun.status == "completed").order_by(Agent1EvaluationRun.completed_at.desc()).first()