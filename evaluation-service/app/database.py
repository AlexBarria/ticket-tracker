from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from typing import Optional, List
import uuid

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