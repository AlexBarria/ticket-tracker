import logging

from fastapi import FastAPI, HTTPException
import os

from guardrails.errors import ValidationError
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prompt_guards import PromptGuards

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Guardrails")


def _setup_tracing(app: FastAPI) -> None:
    try:
        service_name = os.getenv("OTEL_SERVICE_NAME", "guardrails-2-rag")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://phoenix:4317")
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument_app(app)
    except Exception as e:
        logger.error(f"Tracing setup failed: {e}")


_setup_tracing(app)

# Setup Guards
promptGuards = PromptGuards()


class GuardRequest(BaseModel):
    guard: str
    prompt: str


class GuardResponse(BaseModel):
    answer: str


@app.get("/")
def read_root():
    # Health check endpoint
    return {"status": "ok", "service": "Guardrails"}


@app.post("/validate")
def validate(request: GuardRequest):
    if not promptGuards.is_guard(request.guard):
        raise HTTPException(status_code=404, detail="Guard not found")
    try:
        answer = promptGuards.validate(request.guard, request.prompt)
        return GuardResponse(answer=str(answer))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=f"Validation failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
