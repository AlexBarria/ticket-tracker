import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .evaluators.ragas_evaluator import RAGASEvaluator

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None
evaluator: RAGASEvaluator = None


async def run_scheduled_evaluation():
    """Run a scheduled evaluation"""
    global evaluator

    try:
        logger.info("Starting scheduled RAGAS evaluation")
        result = await evaluator.run_evaluation(run_type="scheduled")
        logger.info(f"Scheduled evaluation completed: {result}")
    except Exception as e:
        logger.error(f"Scheduled evaluation failed: {str(e)}")


def start_scheduler():
    """Start the evaluation scheduler"""
    global scheduler, evaluator

    if scheduler is not None:
        logger.warning("Scheduler is already running")
        return

    try:
        # Initialize evaluator
        evaluator = RAGASEvaluator()

        # Create scheduler
        scheduler = AsyncIOScheduler()

        # Parse cron expression
        cron_parts = settings.EVAL_SCHEDULE_CRON.split()
        if len(cron_parts) != 5:
            raise ValueError(f"Invalid cron expression: {settings.EVAL_SCHEDULE_CRON}")

        minute, hour, day, month, day_of_week = cron_parts

        # Add scheduled job
        scheduler.add_job(
            run_scheduled_evaluation,
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            ),
            id="ragas_evaluation",
            name="RAGAS Evaluation",
            max_instances=1,  # Prevent overlapping runs
            coalesce=True     # Coalesce missed runs
        )

        # Start the scheduler
        scheduler.start()

        logger.info(f"Scheduler started with cron expression: {settings.EVAL_SCHEDULE_CRON}")
        logger.info(f"Next evaluation scheduled for: {scheduler.get_job('ragas_evaluation').next_run_time}")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
        raise


def stop_scheduler():
    """Stop the evaluation scheduler"""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler_status():
    """Get the current scheduler status"""
    global scheduler

    if scheduler is None:
        return {
            "status": "stopped",
            "next_run": None,
            "jobs": []
        }

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    next_run = None
    ragas_job = scheduler.get_job('ragas_evaluation')
    if ragas_job and ragas_job.next_run_time:
        next_run = ragas_job.next_run_time.isoformat()

    return {
        "status": "running",
        "next_run": next_run,
        "jobs": jobs
    }


async def trigger_manual_evaluation():
    """Trigger a manual evaluation run"""
    global evaluator

    if evaluator is None:
        evaluator = RAGASEvaluator()

    try:
        logger.info("Starting manual RAGAS evaluation")
        result = await evaluator.run_evaluation(run_type="manual")
        logger.info(f"Manual evaluation completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Manual evaluation failed: {str(e)}")
        raise


async def trigger_sample_evaluation(sample_size: int = 5):
    """Trigger a sample evaluation for testing"""
    global evaluator

    if evaluator is None:
        evaluator = RAGASEvaluator()

    try:
        logger.info(f"Starting sample RAGAS evaluation with {sample_size} queries")
        result = await evaluator.run_sample_evaluation(sample_size=sample_size)
        logger.info(f"Sample evaluation completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Sample evaluation failed: {str(e)}")
        raise