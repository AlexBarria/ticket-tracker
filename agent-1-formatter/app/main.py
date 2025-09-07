# agent-1-formatter/app/main.py
import os
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from minio import Minio
import jwt

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
def upload_receipt(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Receives a receipt image, uploads it to a user-specific folder in MinIO,
    and then (in the future) triggers OCR and formatting.
    """
    try:
        # 1. Upload to MinIO in a user-specific folder
        # Object name will be: "auth0|user_id_123/receipt_name.jpg"
        object_name = f"{user_id}/{file.filename}"
        
        # Ensure the bucket exists
        found = minio_client.bucket_exists(MINIO_BUCKET)
        if not found:
            raise HTTPException(status_code=500, detail=f"MinIO bucket '{MINIO_BUCKET}' does not exist.")

        minio_client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=file.file,
            length=-1, # Auto-detect length
            part_size=10*1024*1024, # Required for stream uploads
            content_type=file.content_type
        )
        
        s3_path = f"s3://{MINIO_BUCKET}/{object_name}"

        # 2. (Future work) Call OCR service with the uploaded file
        # text = call_ocr_service(file)

        # 3. (Future work) Use Agent 1 logic to format the text
        # structured_data = format_text(text)
        
        # 4. (Future work) Save structured_data to PostgreSQL
        # save_to_db(structured_data, s3_path)

        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "user_id": user_id,
            "s3_path": s3_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))