# agent-1-formatter/app/main.py
import os
import io
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from minio import Minio
import jwt
import requests

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

@app.post("/upload-receipt/")
async def upload_receipt(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Receives a receipt image, uploads it to MinIO, calls the OCR service,
    and then (in the future) formats the data.
    """
    try:
        # We need to read the file content to send it to multiple services.
        # Reading it into memory is okay for receipts, but for large files,
        # you'd stream it differently.
        file_content = await file.read()
        
        # 1. Upload to MinIO
        object_name = f"{user_id}/{file.filename}"
        minio_client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=io.BytesIO(file_content), # Use io.BytesIO to treat bytes as a file-like object
            length=len(file_content),
            content_type=file.content_type
        )
        s3_path = f"s3://{MINIO_BUCKET}/{object_name}"

        # 2. Call OCR service with the same file content
        ocr_service_url = "http://ocr-service:8000/scan"
        files = {"file": (file.filename, file_content, file.content_type)}
        
        extracted_text = ""
        try:
            ocr_response = requests.post(ocr_service_url, files=files)
            ocr_response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            extracted_text = ocr_response.json().get("text")
        except requests.exceptions.RequestException as e:
            # If the OCR service is down, we can still proceed but log the error
            print(f"Could not connect to OCR service: {e}")
            # Optionally, raise an HTTPException if OCR is critical
            raise HTTPException(status_code=503, detail="OCR service is unavailable")

        # 3. (Future work) Format the text and save to DB
        # ...

        return {
            "message": "File uploaded and processed by OCR",
            "s3_path": s3_path,
            "extracted_text": extracted_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))