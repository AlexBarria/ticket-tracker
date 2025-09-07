# agent-1-formatter/app/main.py
import os
import io
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from minio import Minio
from sqlalchemy.orm import Session
import jwt
import requests

from . import crud, models, schemas, llm_processor
from .database import SessionLocal, engine


# Create database tables on startup
models.Base.metadata.create_all(bind=engine)

# --- MinIO Configuration ---
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False # Set to True if using HTTPS
)
MINIO_BUCKET = os.getenv("MINIO_BUCKET")

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


@app.get("/")
def read_root():
    return {"status": "ok", "service": "Agent 1 - Formatter"}


@app.post("/upload-receipt/", response_model=schemas.TicketResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_content = await file.read()
    
    # 1. Upload original image to MinIO
    object_name = f"{user_id}/{file.filename}"
    minio_client.put_object(MINIO_BUCKET, object_name, io.BytesIO(file_content), len(file_content), content_type=file.content_type)
    s3_path = f"s3://{MINIO_BUCKET}/{object_name}"

    # 2. Call OCR service to get raw text
    ocr_response = requests.post("http://ocr-service:8000/scan", files={"file": (file.filename, file_content, file.content_type)})
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
