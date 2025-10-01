import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from .config import settings
from .database import engine
from .api.evaluation_routes import router as evaluation_router
from .api.metrics_routes import router as metrics_router
from .api.agent1_evaluation_routes import router as agent1_evaluation_router
from .scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RAGAS Evaluation Service",
    description="Service for evaluating RAG agent performance using RAGAS metrics",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def setup_tracing():
    """Setup OpenTelemetry tracing"""
    try:
        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
            insecure=True
        )

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor().instrument_app(app)

        # Instrument requests
        RequestsInstrumentor().instrument()

        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument(engine=engine)

        logger.info("OpenTelemetry tracing setup completed")

    except Exception as e:
        logger.warning(f"Failed to setup tracing: {e}")


# Setup tracing on startup
setup_tracing()

# Include routers
app.include_router(evaluation_router, prefix="/api/v1/evaluation", tags=["evaluation"])
app.include_router(agent1_evaluation_router, prefix="/api/v1/evaluation/agent1", tags=["agent1-evaluation"])
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["metrics"])


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting RAGAS Evaluation Service")

    # Start the scheduler
    try:
        start_scheduler()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "RAGAS Evaluation Service",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test database connection
        from .database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "service": "RAGAS Evaluation Service",
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=False
    )