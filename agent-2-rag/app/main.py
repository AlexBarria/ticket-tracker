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
def ask(query: dict, token: str = Depends(oauth2_scheme), user_role: str = Depends(get_user_role)):
    import time
    import psycopg2

    if 'admin' not in user_role:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource.")

    question = query.get("query")
    if not question:
        raise HTTPException(status_code=400, detail="Query parameter is required.")

    start_time = time.time()
    success = True
    token_count = 0
    user_id = None

    try:
        # Extract user_id from token
        import jwt
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub", "unknown")

        # Run the pipeline and get token count
        answer, token_count = agent_pipeline.run(question)

        return {"answer": answer, "tokens_used": token_count}

    except Exception as e:
        success = False
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

    finally:
        # Log the query with token usage
        try:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Convert SQLAlchemy DSN to psycopg2 format
            db_url = os.getenv("DATABASE_URL").replace("postgresql+psycopg2://", "postgresql://")

            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agent2_query_logs (query_text, user_id, token_count, response_time_ms, success)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (question, user_id, token_count, response_time_ms, success)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as log_error:
            # Don't fail the request if logging fails
            print(f"Failed to log query: {log_error}")
