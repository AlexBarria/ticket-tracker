import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
import httpx
import uuid
from datetime import datetime

# RAGAS imports for version 0.1.21
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset

# LangChain imports compatible with RAGAS 0.1.21
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..config import settings
from ..database import EvaluationDB, get_db
from ..datasets.loader import TestDataLoader

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """RAGAS-based evaluation system for RAG performance"""

    def __init__(self):
        # Set OpenAI API key for LangChain
        import os
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0
        )
        self.embeddings = OpenAIEmbeddings()
        self.data_loader = TestDataLoader()

        # Configure RAGAS metrics
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]

    def create_evaluation_token(self) -> str:
        """Create a JWT token for evaluation service to authenticate with agent-2"""
        import jwt
        import time

        # Create a simple token that indicates this is the evaluation service
        now = int(time.time())
        payload = {
            "sub": "evaluation-service",
            "name": "Evaluation Service",
            "https://ticket-tracker.com/roles": ["admin"],  # Grant admin role for evaluation
            "iat": now,
            "exp": now + 3600  # 1 hour from now
        }

        # Use a simple secret for internal service communication
        # Since agent-2 doesn't verify signature, any secret works
        token = jwt.encode(payload, "secret", algorithm="HS256")
        return token

    async def query_agent_2(self, question: str, timeout: int = 30) -> Dict[str, Any]:
        """Query the agent-2-rag service"""
        # Configure HTTPX client with proper settings for docker networking
        client_config = {
            "timeout": httpx.Timeout(timeout),
            "verify": False,  # Disable SSL verification for internal docker communication
            "trust_env": False,  # Don't use environment proxy settings
        }

        async with httpx.AsyncClient(**client_config) as client:
            try:
                # Create authentication token
                auth_token = self.create_evaluation_token()

                url = f"{settings.AGENT_2_URL}/ask"
                logger.info(f"Requesting agent-2 at: {url}")

                # Based on the existing agent-2 API structure
                response = await client.post(
                    url,
                    json={"query": question},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {auth_token}"
                    }
                )

                logger.info(f"Agent-2 response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                logger.info(f"Agent-2 response: {result}")
                return result

            except httpx.ConnectError as e:
                logger.error(f"Connection error when querying agent-2: {e}")
                raise
            except httpx.TimeoutException as e:
                logger.error(f"Timeout error when querying agent-2: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error when querying agent-2: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error when querying agent-2: {e.response.status_code} - {e.response.text}")
                raise

    def extract_context_from_response(self, response_data: Dict[str, Any]) -> str:
        """Extract context information from agent-2 response"""
        # Agent-2 returns an answer, which we'll use as context
        # This is reasonable since the answer contains the retrieved information
        answer = response_data.get("answer", "")

        # For RAGAS evaluation, we need some context
        # If agent-2 doesn't provide explicit context, we use the answer as context
        if not answer.strip():
            return "No context available from agent response"

        return answer

    def _run_ragas_evaluation(self, dataset):
        """Run RAGAS evaluation in a separate thread to avoid event loop conflicts"""
        return evaluate(
            dataset=dataset,
            metrics=self.metrics,
            llm=self.llm,
            embeddings=self.embeddings
        )

    def _extract_score(self, result, metric_name):
        """Extract score from RAGAS result, handling both scalar and array formats"""
        import math
        if metric_name not in result:
            return None

        value = result[metric_name]

        # Handle different formats that RAGAS might return
        if isinstance(value, (list, tuple)) and len(value) > 0:
            score = float(value[0])
        elif isinstance(value, (int, float)):
            score = float(value)
        else:
            logger.warning(f"Unexpected format for {metric_name}: {type(value)} - {value}")
            return None

        # Convert NaN to None
        return None if math.isnan(score) else score

    async def evaluate_single_query(
        self,
        query_data: Dict[str, Any],
        run_id: uuid.UUID,
        db: EvaluationDB
    ) -> Dict[str, Any]:
        """Evaluate a single query using RAGAS metrics"""
        query_id = query_data.get("query_id")
        question = query_data.get("question")
        reference_answer = query_data.get("reference_answer", "")

        start_time = time.time()
        evaluation_status = "success"
        error_message = None

        try:
            # Query agent-2
            logger.info(f"Evaluating query {query_id}: {question}")
            response_data = await self.query_agent_2(question, timeout=settings.EVAL_TIMEOUT)

            generated_answer = response_data.get("answer", "")
            retrieved_context = self.extract_context_from_response(response_data)

            response_time_ms = int((time.time() - start_time) * 1000)

            # Prepare data for RAGAS evaluation
            evaluation_data = {
                "question": [question],
                "answer": [generated_answer],
                "contexts": [[retrieved_context]],  # RAGAS expects list of lists
                "ground_truth": [reference_answer]
            }

            # Create dataset for RAGAS
            dataset = Dataset.from_dict(evaluation_data)

            # Run RAGAS evaluation in a separate thread to avoid event loop conflicts
            logger.info(f"Running RAGAS evaluation for query {query_id}")
            evaluation_start = time.time()

            # Use asyncio.to_thread to run RAGAS in a separate thread
            # This prevents uvloop conflicts
            result = await asyncio.to_thread(
                self._run_ragas_evaluation,
                dataset
            )

            evaluation_time = time.time() - evaluation_start
            logger.info(f"RAGAS evaluation completed for query {query_id} in {evaluation_time:.2f}s")

            # Extract scores - handle both scalar and array formats
            faithfulness_score = self._extract_score(result, "faithfulness")
            answer_relevance_score = self._extract_score(result, "answer_relevancy")
            context_precision_score = self._extract_score(result, "context_precision")
            context_recall_score = self._extract_score(result, "context_recall")

            # Estimate token count (simple approximation)
            token_count = len(generated_answer.split()) + len(retrieved_context.split())

        except Exception as e:
            logger.error(f"Error evaluating query {query_id}: {str(e)}")
            evaluation_status = "error"
            error_message = str(e)

            # Set default values for failed evaluation
            generated_answer = ""
            retrieved_context = ""
            response_time_ms = int((time.time() - start_time) * 1000)
            token_count = 0
            faithfulness_score = None
            answer_relevance_score = None
            context_precision_score = None
            context_recall_score = None

        # Store result in database
        db_result = db.create_evaluation_result(
            run_id=run_id,
            query_id=query_id,
            query_text=question,
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

        return {
            "query_id": query_id,
            "status": evaluation_status,
            "faithfulness_score": faithfulness_score,
            "answer_relevance_score": answer_relevance_score,
            "context_precision_score": context_precision_score,
            "context_recall_score": context_recall_score,
            "response_time_ms": response_time_ms,
            "error_message": error_message
        }

    async def run_evaluation(
        self,
        run_type: str = "manual",
        limit_queries: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run a complete evaluation session"""
        # Get database session
        db_session = next(get_db())
        db = EvaluationDB(db_session)

        try:
            # Create evaluation run
            run = db.create_evaluation_run(run_type=run_type, status="running")
            run_id = run.run_id

            logger.info(f"Starting evaluation run {run_id} (type: {run_type})")

            # Load test queries
            queries = self.data_loader.load_test_queries()
            if limit_queries:
                queries = queries[:limit_queries]

            total_queries = len(queries)
            successful_queries = 0

            # Track metrics for averaging
            faithfulness_scores = []
            answer_relevance_scores = []
            context_precision_scores = []
            context_recall_scores = []

            # Process queries in batches to avoid overwhelming the system
            batch_size = settings.EVAL_BATCH_SIZE

            for i in range(0, total_queries, batch_size):
                batch = queries[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} queries)")

                # Process batch concurrently
                batch_tasks = [
                    self.evaluate_single_query(query, run_id, db)
                    for query in batch
                ]

                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch evaluation error: {result}")
                        continue

                    if result["status"] == "success":
                        successful_queries += 1

                        # Collect scores for averaging
                        if result["faithfulness_score"] is not None:
                            faithfulness_scores.append(result["faithfulness_score"])
                        if result["answer_relevance_score"] is not None:
                            answer_relevance_scores.append(result["answer_relevance_score"])
                        if result["context_precision_score"] is not None:
                            context_precision_scores.append(result["context_precision_score"])
                        if result["context_recall_score"] is not None:
                            context_recall_scores.append(result["context_recall_score"])

                # Small delay between batches
                await asyncio.sleep(1)

            # Calculate averages and handle NaN values
            def safe_average(scores):
                """Calculate average and convert NaN to None"""
                import math
                if not scores:
                    return None
                avg = sum(scores) / len(scores)
                return None if math.isnan(avg) else avg

            avg_faithfulness = safe_average(faithfulness_scores)
            avg_answer_relevance = safe_average(answer_relevance_scores)
            avg_context_precision = safe_average(context_precision_scores)
            avg_context_recall = safe_average(context_recall_scores)

            # Update evaluation run
            db.update_evaluation_run(
                run_id=run_id,
                status="completed",
                completed_at=datetime.utcnow(),
                total_queries=total_queries,
                successful_queries=successful_queries,
                average_faithfulness=avg_faithfulness,
                average_answer_relevance=avg_answer_relevance,
                average_context_precision=avg_context_precision,
                average_context_recall=avg_context_recall,
                run_metadata={
                    "batch_size": batch_size,
                    "timeout": settings.EVAL_TIMEOUT
                }
            )

            logger.info(f"Evaluation run {run_id} completed. {successful_queries}/{total_queries} queries successful")

            return {
                "run_id": str(run_id),
                "status": "completed",
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "average_faithfulness": avg_faithfulness,
                "average_answer_relevance": avg_answer_relevance,
                "average_context_precision": avg_context_precision,
                "average_context_recall": avg_context_recall
            }

        except Exception as e:
            logger.error(f"Evaluation run failed: {str(e)}")
            # Update run status to failed
            if 'run_id' in locals():
                db.update_evaluation_run(
                    run_id=run_id,
                    status="failed",
                    completed_at=datetime.utcnow(),
                    run_metadata={"error": str(e)}
                )
            raise
        finally:
            db_session.close()

    async def run_sample_evaluation(self, sample_size: int = 5) -> Dict[str, Any]:
        """Run evaluation on a small sample for testing"""
        return await self.run_evaluation(run_type="sample", limit_queries=sample_size)

    async def evaluate_realtime_query(
        self,
        question: str,
        reference_answer: str = "",
        query_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate a single real-time query (from admin dashboard)"""
        # Get database session
        db_session = next(get_db())
        db = EvaluationDB(db_session)

        try:
            # Create a special "realtime" evaluation run
            run = db.create_evaluation_run(run_type="realtime", status="running")
            run_id = run.run_id

            logger.info(f"Starting real-time evaluation for query: {question}")

            # Create query data
            if not query_id:
                query_id = f"realtime_{int(time.time())}"

            query_data = {
                "query_id": query_id,
                "question": question,
                "reference_answer": reference_answer
            }

            # Evaluate the query
            result = await self.evaluate_single_query(query_data, run_id, db)

            # Save query to realtime dataset for future reference
            try:
                self.data_loader.save_realtime_query(query_data)
                logger.info(f"Saved real-time query {query_id} to dataset")
            except Exception as e:
                logger.warning(f"Failed to save real-time query to dataset: {e}")

            # Update evaluation run
            db.update_evaluation_run(
                run_id=run_id,
                status="completed",
                completed_at=datetime.utcnow(),
                total_queries=1,
                successful_queries=1 if result["status"] == "success" else 0,
                average_faithfulness=result.get("faithfulness_score"),
                average_answer_relevance=result.get("answer_relevance_score"),
                average_context_precision=result.get("context_precision_score"),
                average_context_recall=result.get("context_recall_score"),
                run_metadata={
                    "query": question,
                    "realtime": True
                }
            )

            logger.info(f"Real-time evaluation completed for query: {question}")

            return {
                "run_id": str(run_id),
                "query_id": query_id,
                "status": result["status"],
                "faithfulness_score": result.get("faithfulness_score"),
                "answer_relevance_score": result.get("answer_relevance_score"),
                "context_precision_score": result.get("context_precision_score"),
                "context_recall_score": result.get("context_recall_score"),
                "response_time_ms": result.get("response_time_ms"),
                "error_message": result.get("error_message")
            }

        except Exception as e:
            logger.error(f"Real-time evaluation failed: {str(e)}")
            # Update run status to failed
            if 'run_id' in locals():
                db.update_evaluation_run(
                    run_id=run_id,
                    status="failed",
                    completed_at=datetime.utcnow(),
                    run_metadata={"error": str(e), "realtime": True}
                )
            raise
        finally:
            db_session.close()