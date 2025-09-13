import io
import streamlit as st
from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import easyocr
import numpy as np
import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

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

def _setup_tracing(app: FastAPI) -> None:
    try:
        service_name = os.getenv("OTEL_SERVICE_NAME", "ocr-service")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://phoenix:4317")
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument_app(app)
    except Exception:
        # best effort; do not crash
        pass

_setup_tracing(app)

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