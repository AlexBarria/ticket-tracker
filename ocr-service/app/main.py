import io
import streamlit as st
from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import easyocr
import numpy as np

# --- Model Loading ---

# This is a critical optimization:
# We load the model only once when the application starts.
# This avoids reloading the heavy model on every API request.
# We include Spanish ('es') and English ('en') as languages.
try:
    reader = easyocr.Reader(['es', 'en'], gpu=False)
except Exception as e:
    reader = None
    st.error(f"Error loading EasyOCR model: {e}")


# --- FastAPI App ---

app = FastAPI(title="OCR Service")

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "OCR Service"}

@app.post("/scan")
async def scan_receipt(file: UploadFile = File(...)):
    """
    Receives an image file, extracts text using EasyOCR, and returns the text.
    """
    if not reader:
        raise HTTPException(status_code=500, detail="OCR model is not available.")
    
    # Read the image file from the upload
    image_bytes = await file.read()
    
    try:
        # Use EasyOCR to read text from the image bytes
        # The 'detail=0' argument returns a simple list of strings.
        result = reader.readtext(image_bytes, detail=0, paragraph=False)
        
        # Join the extracted lines of text into a single string
        extracted_text = "\n".join(result)
        
        return {
            "filename": file.filename,
            "text": extracted_text
        }
    except Exception as e:
        # This will catch errors from EasyOCR if the image is corrupt or unreadable
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")