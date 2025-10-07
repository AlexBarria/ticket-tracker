import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
import httpx
import uuid
from datetime import datetime, date
from decimal import Decimal

from langchain_openai import ChatOpenAI
from openai import OpenAI

from ..config import settings
from ..database import get_db, EvaluationDB
from ..datasets.loader import TestDataLoader

logger = logging.getLogger(__name__)


class Agent1Evaluator:
    """Evaluator for Agent 1 (OCR + Formatter) performance"""

    def __init__(self):
        # Initialize OpenAI for LLM-as-judge
        import os
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0
        )
        self.openai_client = OpenAI()
        self.data_loader = TestDataLoader()

    def fetch_ticket_from_db(self, ticket_id: int) -> Dict[str, Any]:
        """Fetch a ticket from the database by ID"""
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, merchant_name, transaction_date, total_amount, items, category, s3_path, user_id FROM tickets WHERE id = :id"),
                {"id": ticket_id}
            ).fetchone()

            if not result:
                raise ValueError(f"Ticket {ticket_id} not found in database")

            # Convert row to dict
            return {
                "id": result[0],
                "merchant_name": result[1],
                "transaction_date": str(result[2]) if result[2] else None,
                "total_amount": float(result[3]) if result[3] else None,
                "items": result[4],  # JSONB
                "category": result[5],
                "s3_path": result[6],
                "user_id": result[7]
            }

    # ==================== DETERMINISTIC METRICS ====================

    def calculate_exact_match(self, expected: Any, actual: Any) -> bool:
        """Calculate exact match for a field"""
        if expected is None and actual is None:
            return True
        if expected is None or actual is None:
            return False

        # Normalize strings (case-insensitive, strip whitespace)
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.strip().lower() == actual.strip().lower()

        # For dates
        if isinstance(expected, (date, str)) and isinstance(actual, (date, str)):
            expected_str = str(expected) if not isinstance(expected, str) else expected
            actual_str = str(actual) if not isinstance(actual, str) else actual
            return expected_str == actual_str

        # For amounts (allow small floating point differences)
        if isinstance(expected, (int, float, Decimal, str)) and isinstance(actual, (int, float, Decimal, str)):
            try:
                expected_val = float(expected) if not isinstance(expected, float) else expected
                actual_val = float(actual) if not isinstance(actual, float) else actual
                return abs(expected_val - actual_val) < 0.01  # Tolerance of 1 cent
            except (ValueError, TypeError):
                return False

        return expected == actual

    def calculate_item_metrics(self, expected_items: List[Dict], actual_items: List[Dict]) -> Tuple[float, float, float]:
        """
        Calculate precision, recall, and F1 score for item extraction

        Items are matched based on description similarity and price matching
        """
        logger.info(f"Calculating item metrics - Expected: {len(expected_items)} items, Actual: {len(actual_items)} items")
        logger.info(f"Expected items: {expected_items}")
        logger.info(f"Actual items: {actual_items}")

        if not expected_items and not actual_items:
            return 1.0, 1.0, 1.0

        if not expected_items or not actual_items:
            return 0.0, 0.0, 0.0

        # Track which items have been matched
        matched_expected = set()
        matched_actual = set()

        # Try to match each expected item with an actual item
        for exp_idx, exp_item in enumerate(expected_items):
            exp_desc = exp_item.get('description', '').strip().lower()
            exp_price = exp_item.get('price', '')

            for act_idx, act_item in enumerate(actual_items):
                if act_idx in matched_actual:
                    continue

                act_desc = act_item.get('description', '').strip().lower()
                act_price = act_item.get('price', '')

                # Check if description and price match (fuzzy)
                desc_match = exp_desc == act_desc or exp_desc in act_desc or act_desc in exp_desc
                price_match = self.calculate_exact_match(exp_price, act_price)

                if desc_match and price_match:
                    matched_expected.add(exp_idx)
                    matched_actual.add(act_idx)
                    break

        # Calculate metrics
        true_positives = len(matched_expected)
        false_positives = len(actual_items) - len(matched_actual)
        false_negatives = len(expected_items) - len(matched_expected)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return precision, recall, f1

    # ==================== LLM-AS-JUDGE METRICS ====================

    def llm_evaluate_merchant_similarity(self, expected: str, actual: str) -> Tuple[float, int]:
        """Use LLM to evaluate semantic similarity of merchant names
        Returns: (similarity_score, token_count)
        """
        prompt = f"""You are evaluating OCR extraction quality. Rate the similarity between these two merchant names on a scale of 0.0 to 1.0.

Expected: "{expected}"
Actual: "{actual}"

Scoring Guide:
- 1.0 = Perfect match (identical)
- 0.9-0.95 = Same merchant, only case/spacing differences (e.g., "WALMART" vs "Walmart")
- 0.8-0.85 = Same merchant, minor OCR errors (1-2 character substitutions like I→L, O→0)
- 0.7-0.75 = Same merchant, moderate OCR errors (3-4 character substitutions or missing characters)
- 0.5-0.65 = Recognizable as same merchant but significant errors
- 0.0-0.4 = Different merchants entirely

Common OCR Confusions to Treat as High Similarity:
- I vs L vs 1
- O vs 0
- S vs 5
- B vs 8
- Mixed/wrong capitalization
- Missing or extra spaces

Examples:
"GRAND LUX CAFE" vs "GRAND IIXEAFE" → 0.75
"Walmart" vs "WALMART" → 0.95
"Starbucks" vs "Target" → 0.0
"GREEN FIELD" vs "greEN FteLD" → 0.80

Output ONLY the numeric score (e.g., 0.85). No explanation, no text, just the number."""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            score_str = response.choices[0].message.content.strip()
            score = float(score_str)
            tokens = response.usage.total_tokens if response.usage else 0
            return max(0.0, min(1.0, score)), tokens

        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
            # Fallback to simple string similarity
            return (1.0 if expected.lower() == actual.lower() else 0.0), 0

    def llm_evaluate_items_similarity(self, expected_items: List[Dict], actual_items: List[Dict]) -> Tuple[float, int]:
        """Use LLM to evaluate item extraction quality
        Returns: (similarity_score, token_count)
        """
        prompt = f"""Rate the quality of item extraction from a receipt. Compare expected vs actual items.

Expected Items:
{json.dumps(expected_items, indent=2)}

Actual Extracted Items:
{json.dumps(actual_items, indent=2)}

Scoring Guide (0.0-1.0):
- 1.0 = Perfect match (all items correct, prices exact)
- 0.9-0.95 = All items found, prices within $0.50, minor description errors
- 0.8-0.85 = All items found, some prices off by $1-2, moderate OCR errors
- 0.7-0.75 = 1-2 items missing OR extra, or significant price errors ($3+)
- 0.5-0.65 = Half the items correct, major errors
- 0.3-0.4 = Few items correct, mostly wrong
- 0.0-0.2 = Almost nothing correct

Evaluation Criteria:
- Missing items: Reduce score significantly (each missing item = -0.15)
- Extra wrong items: Reduce score moderately (each wrong item = -0.10)
- Description OCR errors: Reduce score slightly if meaning is preserved
  (e.g., "Cofee" vs "Coffee" = minor, "Bread" vs "Meat" = major)
- Price accuracy: Must be within $1.00 for high scores
- Item order doesn't matter

Examples:
Expected: [{{"description": "Coffee", "price": 3.50}}, {{"description": "Muffin", "price": 4.00}}]
Actual: [{{"description": "Cofee", "price": 3.50}}, {{"description": "Muffin", "price": 4.00}}]
Score: 0.95 (minor OCR error in description)

Expected: [{{"description": "Coffee", "price": 3.50}}, {{"description": "Muffin", "price": 4.00}}]
Actual: [{{"description": "Coffee", "price": 3.50}}]
Score: 0.50 (one item missing = 50% recall)

Expected: [{{"description": "Lunch", "price": 45.90}}]
Actual: [{{"description": "Lunch Special", "price": 45.90}}]
Score: 0.90 (description close enough, price exact)

Output ONLY the numeric score (e.g., 0.85). No explanation, no text, just the number."""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )

            score_str = response.choices[0].message.content.strip()
            score = float(score_str)
            tokens = response.usage.total_tokens if response.usage else 0
            return max(0.0, min(1.0, score)), tokens

        except Exception as e:
            logger.error(f"LLM items evaluation error: {e}")
            # Fallback to deterministic F1 score
            _, _, f1 = self.calculate_item_metrics(expected_items, actual_items)
            return f1, 0

    def llm_evaluate_overall_quality(self, expected: Dict, actual: Dict) -> Tuple[float, str, int]:
        """Use LLM to evaluate overall extraction quality and provide feedback
        Returns: (quality_score, feedback, token_count)
        """
        prompt = f"""Evaluate OCR receipt extraction quality by comparing expected vs actual data.

Expected:
{json.dumps(expected, indent=2)}

Actual:
{json.dumps(actual, indent=2)}

Scoring Guide (0.0-1.0):
- 1.0 = Perfect: All fields correct
- 0.9 = Excellent: All fields present, minor OCR errors only
- 0.8 = Good: All fields present, some moderate OCR errors or small price discrepancies (<$2)
- 0.7 = Fair: 1 field missing/wrong, or major errors in descriptions
- 0.6 = Poor: 2+ fields missing/wrong
- 0.5 = Very Poor: Multiple critical errors
- <0.5 = Failed: Mostly incorrect

Field Importance (for scoring):
- Merchant name: Critical (30%)
- Total amount: Critical (30%)
- Transaction date: Important (20%)
- Items: Important (20%)

Evaluation Checklist:
✓ Merchant name: Exact match or semantically equivalent?
✓ Total amount: Within $0.50?
✓ Date: Correct format and value?
✓ Items: All captured? Prices match?

Examples:
Expected: {{"merchant_name":"Walmart","total_amount":45.67,"date":"2024-09-15","items":[...]}}
Actual: {{"merchant_name":"WALMART","total_amount":45.67,"date":"2024-09-15","items":[...]}}
Score: 0.95, Feedback: "Excellent extraction. Only merchant name capitalization differs."

Expected: {{"merchant_name":"Starbucks","total_amount":12.50,"date":"2024-09-15","items":[{{"description":"Coffee","price":3.50}}]}}
Actual: {{"merchant_name":"Strbucks","total_amount":12.50,"date":"2024-09-15","items":[]}}
Score: 0.65, Feedback: "Merchant has minor OCR error. Date and total correct. Critical issue: No items extracted."

Respond with ONLY this JSON:
{{
  "score": 0.85,
  "feedback": "Brief assessment of what was correct and what had errors"
}}

Keep feedback under 100 words, focused on actionable issues."""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            score = float(result.get("score", 0.0))
            feedback = result.get("feedback", "")
            tokens = response.usage.total_tokens if response.usage else 0
            return max(0.0, min(1.0, score)), feedback, tokens

        except Exception as e:
            logger.error(f"LLM overall evaluation error: {e}")
            return 0.5, "Evaluation error occurred", 0

    # ==================== EVALUATION ORCHESTRATION ====================

    async def evaluate_single_ticket(
        self,
        ticket_id: int,
        expected: Dict[str, Any],
        run_id: uuid.UUID,
        db: Any
    ) -> Dict[str, Any]:
        """Evaluate a single ticket by fetching it from the database"""
        start_time = time.time()
        evaluation_status = "success"
        error_message = None

        try:
            logger.info(f"Evaluating ticket ID {ticket_id}")

            # Fetch the actual ticket data from database (already processed by Agent 1)
            actual_ticket = self.fetch_ticket_from_db(ticket_id)

            logger.info(f"Fetched ticket {ticket_id} from database: merchant={actual_ticket.get('merchant_name')}, items count={len(actual_ticket.get('items', []))}")

            # Extract actual values
            actual = {
                "merchant_name": actual_ticket.get("merchant_name", ""),
                "transaction_date": actual_ticket.get("transaction_date", ""),
                "total_amount": actual_ticket.get("total_amount", ""),
                "items": actual_ticket.get("items", [])
            }

            logger.info(f"Expected values: merchant={expected.get('merchant_name')}, items count={len(expected.get('items', []))}")

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Calculate deterministic metrics
            merchant_match = self.calculate_exact_match(
                expected.get("merchant_name"), actual["merchant_name"]
            )
            date_match = self.calculate_exact_match(
                expected.get("transaction_date"), actual["transaction_date"]
            )
            amount_match = self.calculate_exact_match(
                expected.get("total_amount"), actual["total_amount"]
            )

            item_precision, item_recall, item_f1 = self.calculate_item_metrics(
                expected.get("items", []), actual["items"]
            )

            # Calculate LLM-as-judge metrics
            logger.info(f"Running LLM evaluation for ticket {ticket_id}")
            merchant_similarity, tokens_merchant = self.llm_evaluate_merchant_similarity(
                expected.get("merchant_name", ""), actual["merchant_name"]
            )
            items_similarity, tokens_items = self.llm_evaluate_items_similarity(
                expected.get("items", []), actual["items"]
            )
            overall_quality, llm_feedback, tokens_overall = self.llm_evaluate_overall_quality(expected, actual)

            # Sum total tokens used in LLM evaluations
            total_tokens = tokens_merchant + tokens_items + tokens_overall

            logger.info(f"Evaluation completed for ticket {ticket_id} (used {total_tokens} tokens)")

        except Exception as e:
            logger.error(f"Error evaluating ticket {ticket_id}: {str(e)}")
            evaluation_status = "error"
            error_message = str(e)

            # Set default values
            processing_time_ms = int((time.time() - start_time) * 1000)
            actual = {"merchant_name": "", "transaction_date": "", "total_amount": "", "items": []}
            merchant_match = date_match = amount_match = False
            item_precision = item_recall = item_f1 = 0.0
            merchant_similarity = items_similarity = overall_quality = 0.0
            llm_feedback = ""
            total_tokens = 0

        # Prepare result dictionary
        result = {
            "test_id": str(ticket_id),
            "filename": f"ticket_{ticket_id}",
            "expected": expected,
            "actual": actual,
            "merchant_match": merchant_match,
            "date_match": date_match,
            "amount_match": amount_match,
            "item_precision": item_precision,
            "item_recall": item_recall,
            "item_f1": item_f1,
            "merchant_similarity": merchant_similarity,
            "items_similarity": items_similarity,
            "overall_quality": overall_quality,
            "llm_feedback": llm_feedback,
            "processing_time_ms": processing_time_ms,
            "token_count": total_tokens,
            "evaluation_status": evaluation_status,
            "error_message": error_message
        }

        # Store in DB
        if db:
            db.create_agent1_evaluation_result(run_id, result)

        return result

    async def evaluate_realtime_ticket(
        self,
        ticket_id: int,
        expected_merchant: str,
        expected_date: str,
        expected_amount: float,
        expected_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate a single ticket in real-time (called from UI)"""
        db_session = next(get_db())
        db = EvaluationDB(db_session)

        try:
            # Create evaluation run for this single ticket
            run = db.create_agent1_evaluation_run(run_type="realtime", status="running")
            run_id = run.run_id

            # Prepare expected output
            expected = {
                "merchant_name": expected_merchant,
                "transaction_date": expected_date,
                "total_amount": expected_amount,
                "items": expected_items
            }

            # Evaluate the ticket
            result = await self.evaluate_single_ticket(ticket_id, expected, run_id, db)

            # Update run with results
            token_count = result.get("token_count", 0)
            db.update_agent1_evaluation_run(
                run_id=run_id,
                status="completed",
                completed_at=datetime.utcnow(),
                total_tickets=1,
                successful_tickets=1 if result["evaluation_status"] == "success" else 0,
                average_merchant_match=1.0 if result.get("merchant_match") else 0.0,
                average_date_match=1.0 if result.get("date_match") else 0.0,
                average_amount_match=1.0 if result.get("amount_match") else 0.0,
                average_item_precision=result.get("item_precision", 0.0),
                average_item_recall=result.get("item_recall", 0.0),
                average_item_f1=result.get("item_f1", 0.0),
                average_merchant_similarity=result.get("merchant_similarity", 0.0),
                average_items_similarity=result.get("items_similarity", 0.0),
                average_overall_quality=result.get("overall_quality", 0.0),
                total_tokens=token_count,
                average_tokens_per_ticket=float(token_count)
            )

            return {
                "run_id": str(run_id),
                "ticket_id": ticket_id,
                "evaluation_status": result["evaluation_status"],
                "metrics": {
                    "merchant_match": result.get("merchant_match"),
                    "date_match": result.get("date_match"),
                    "amount_match": result.get("amount_match"),
                    "item_precision": result.get("item_precision"),
                    "item_recall": result.get("item_recall"),
                    "item_f1": result.get("item_f1"),
                    "merchant_similarity": result.get("merchant_similarity"),
                    "items_similarity": result.get("items_similarity"),
                    "overall_quality": result.get("overall_quality")
                },
                "llm_feedback": result.get("llm_feedback"),
                "expected": expected,
                "actual": result.get("actual")
            }

        except Exception as e:
            logger.error(f"Real-time evaluation failed: {str(e)}")
            if 'run_id' in locals():
                db.update_agent1_evaluation_run(
                    run_id=run_id,
                    status="failed",
                    completed_at=datetime.utcnow(),
                    run_metadata={"error": str(e)}
                )
            raise
        finally:
            db_session.close()
