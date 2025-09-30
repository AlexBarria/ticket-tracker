import os
from typing import Optional


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@postgres:5432/tickets_db")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Agent-2 RAG service
    AGENT_2_URL: str = os.getenv("AGENT_2_URL", "http://agent-2-rag:8000")

    # Evaluation settings
    EVAL_SCHEDULE_CRON: str = os.getenv("EVAL_SCHEDULE_CRON", "0 2 * * *")  # 2 AM daily
    EVAL_BATCH_SIZE: int = int(os.getenv("EVAL_BATCH_SIZE", "5"))
    EVAL_TIMEOUT: int = int(os.getenv("EVAL_TIMEOUT", "30"))  # seconds

    # OpenTelemetry
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "evaluation-service")
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://phoenix:4317")
    OTEL_EXPORTER_OTLP_PROTOCOL: str = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")

    # Service settings
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8006"))

    # RAGAS settings
    RAGAS_EMBEDDINGS_MODEL: str = os.getenv("RAGAS_EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


settings = Settings()