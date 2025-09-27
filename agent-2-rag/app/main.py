from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from graph_processor import AgentPipeline
import jwt
import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from openinference.instrumentation.groq import GroqInstrumentor

agent_pipeline = AgentPipeline()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Agent 2 - RAG")


def _setup_tracing(app: FastAPI) -> None:
    try:
        service_name = os.getenv("OTEL_SERVICE_NAME", "agent-2-rag")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://phoenix:4317")
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()
        GroqInstrumentor().instrument()
    except Exception as e:
        # Avoid crashing if tracing fails
        pass


_setup_tracing(app)


def get_user_role(token: str = Depends(oauth2_scheme)):
    """Decodes the JWT to get the user ID ('sub')."""
    try:
        # For simplicity, we decode without full verification here.
        # In production, you should verify the token signature against Auth0's public key.
        payload = jwt.decode(token, options={"verify_signature": False})
        user_name = payload.get("name", "User")
        if user_name is None:
            raise HTTPException(status_code=401, detail="Invalid token: user ID not found")
        namespace = 'https://ticket-tracker.com'
        return payload.get(f'{namespace}/roles', [])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


@app.get("/")
def read_root():
    # Health check endpoint
    return {"status": "ok", "service": "Agent 2 - RAG"}


@app.post("/ask")
def ask(query: dict, user_role: str = Depends(get_user_role)):
    if 'admin' not in user_role:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource.")
    try:
        question = query.get("query")
        if not question:
            raise HTTPException(status_code=400, detail="Query parameter is required.")
        answer = agent_pipeline.run(question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
