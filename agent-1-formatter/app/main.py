# agent-1-formatter/app/main.py
import os
import io
import logging
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, Response
from fastapi.security import OAuth2PasswordBearer
from minio import Minio
from sqlalchemy.orm import Session
import jwt
import requests
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from . import crud, models, schemas, llm_processor
from .database import SessionLocal, engine

# Create database tables on startup
models.Base.metadata.create_all(bind=engine)

# --- MinIO Configuration ---
logger = logging.getLogger(__name__)

minio_client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False  # Set to True if using HTTPS
)
MINIO_BUCKET = os.getenv("MINIO_BUCKET")

# Ensure the bucket exists at startup (best-effort)
if not MINIO_BUCKET:
    logger.error("MINIO_BUCKET environment variable is not set")
else:
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            logger.info(f"Created MinIO bucket '{MINIO_BUCKET}'")
        else:
            logger.info(f"MinIO bucket '{MINIO_BUCKET}' already exists")
    except Exception as e:
        # Do not crash the app on startup; endpoint will attempt again on demand
        logger.warning(f"Could not verify/create MinIO bucket '{MINIO_BUCKET}': {e}")

# --- Auth Configuration ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decodes the JWT to get the user ID ('sub')."""
    try:
        # For simplicity, we decode without full verification here.
        # In production, you should verify the token signature against Auth0's public key.
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: user ID not found")
        return user_id
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# --- FastAPI App ---
app = FastAPI(title="Agent 1 - Formatter & Uploader")


def _setup_tracing(app: FastAPI) -> None:
    try:
        service_name = os.getenv("OTEL_SERVICE_NAME", "agent-1-formatter")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://phoenix:4317")
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Tracing setup failed: {e}")


_setup_tracing(app)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "Agent 1 - Formatter"}


@app.post("/upload-receipt/", response_model=schemas.TicketResponse)
async def upload_receipt(
        file: UploadFile = File(...),
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)):
    file_content = await file.read()
    # 1. Upload original image to MinIO
    object_name = f"{user_id}/{file.filename}"
    # Ensure bucket exists in case startup check raced with init job
    if not minio_client.bucket_exists(MINIO_BUCKET):
        try:
            minio_client.make_bucket(MINIO_BUCKET)
        except Exception:
            # If creation fails because another process created it meanwhile, just proceed
            pass
    minio_client.put_object(
        MINIO_BUCKET,
        object_name,
        io.BytesIO(file_content),
        len(file_content),
        content_type=file.content_type,
    )
    s3_path = f"s3://{MINIO_BUCKET}/{object_name}"

    # 2. Call OCR service to get raw text
    ocr_response = requests.post("http://ocr-service:8000/scan",
                                 files={"file": (file.filename, file_content, file.content_type)})
    if ocr_response.status_code != 200:
        raise HTTPException(status_code=503, detail=f"OCR service failed: {ocr_response.text}")
    extracted_text = ocr_response.json().get("text")

    # 3. Call LLM to structure the text
    try:
        structured_data = llm_processor.structure_receipt_text(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {str(e)}")

    # 4. Save the structured data to the database
    db_ticket = crud.create_ticket(db=db, ticket_data=structured_data, s3_path=s3_path, user_id=user_id)

    return db_ticket


@app.post("/approve-receipt/", response_model=schemas.TicketApproveVerifyResponse)
async def approve_receipt(
        request: schemas.TicketApproveVerifyRequest,
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)):
    try:
        if crud.approve_ticket(db=db, id=request.id, user_id=user_id) is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return schemas.TicketApproveVerifyResponse(status="approved", id=request.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.post("/verify-receipt/", response_model=schemas.TicketApproveVerifyResponse)
async def verify_receipt(
        request: schemas.TicketApproveVerifyRequest,
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)):
    try:
        if crud.verify_ticket(db=db, id=request.id, user_id=user_id) is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return schemas.TicketApproveVerifyResponse(status="approved", id=request.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@app.get("/api/tickets")
async def get_tickets(
        limit: int = 10,
        need_verify: bool = Query(None),
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)):
    """Get recent tickets for the current user"""
    import traceback
    try:
        tickets = crud.get_user_tickets(db=db, user_id=user_id, limit=limit, need_verify=need_verify)

        # Convert SQLAlchemy objects to dicts
        tickets_data = []
        for ticket in tickets:
            tickets_data.append({
                "id": ticket.id,
                "merchant_name": ticket.merchant_name,
                "transaction_date": str(ticket.transaction_date) if ticket.transaction_date else None,
                "total_amount": ticket.total_amount,
                "category": ticket.category,
                "items": ticket.items,
                "s3_path": ticket.s3_path,
                "user_id": ticket.user_id,
                "need_verify": ticket.need_verify,
                "approved": ticket.approved
            })

        return tickets_data
    except Exception as e:
        print(f"ERROR in get_tickets: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickets: {str(e)}")

@app.post("/api/save-ground-truth")
async def save_ground_truth(
    request: dict,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save ground truth for a ticket after evaluation"""
    import json
    try:
        ticket_id = request.get("ticket_id")
        corrected_merchant = request.get("corrected_merchant")
        corrected_date = request.get("corrected_date")
        corrected_amount = request.get("corrected_amount")
        corrected_items = request.get("corrected_items")

        # Convert items to JSON string for JSONB storage
        corrected_items_json = json.dumps(corrected_items)

        crud.save_ground_truth(
            db=db,
            ticket_id=ticket_id,
            corrected_merchant=corrected_merchant,
            corrected_date=corrected_date,
            corrected_amount=corrected_amount,
            corrected_items=corrected_items_json,
            corrected_by=user_id
        )

        return {"status": "success", "message": "Ground truth saved and ticket approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save ground truth: {str(e)}")


@app.get("/api/image")
def get_image(
    s3_path: str = Query(...)
):
    """
    Streams an image from MinIO given its s3_path.
    """
    try:
        if not s3_path.startswith("s3://"):
            raise HTTPException(status_code=400, detail="Invalid s3_path format")
        path = s3_path[5:]
        bucket, object_name = path.split("/", 1)

        data = minio_client.get_object(bucket, object_name)
        image_bytes = data.read()

        # Infer MIME type from file extension
        if object_name.lower().endswith(".png"):
            mime_type = "image/png"
        elif object_name.lower().endswith(".jpg") or object_name.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "application/octet-stream"  # fallback

        return Response(content=image_bytes, media_type=mime_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Image not found: {str(e)}")


@app.get("/api/tickets/all")
def get_all_tickets(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get all tickets from the database for admin dashboard.
    Returns all fields including approval status and verification flags.
    """
    try:
        # Query all tickets ordered by ID descending
        tickets = db.query(models.Ticket).order_by(models.Ticket.id.desc()).all()

        # Convert to list of dicts
        result = []
        for ticket in tickets:
            result.append({
                "id": ticket.id,
                "merchant_name": ticket.merchant_name,
                "transaction_date": str(ticket.transaction_date) if ticket.transaction_date else None,
                "total_amount": float(ticket.total_amount) if ticket.total_amount else 0.0,
                "category": ticket.category,
                "items": ticket.items,
                "s3_path": ticket.s3_path,
                "user_id": ticket.user_id,
                "need_verify": ticket.need_verify,
                "approved": ticket.approved,
                "has_ground_truth": ticket.has_ground_truth
            })

        return result

    except Exception as e:
        logger.error(f"Error fetching all tickets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching tickets: {str(e)}")