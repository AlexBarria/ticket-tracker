# Basic FastAPI application
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="OCR Service")

class Item(BaseModel):
    data: str

@app.get("/")
def read_root():
    # Health check endpoint
    return {"status": "ok", "service": "OCR Service"}

@app.post("/process")
def process_data(item: Item):
    # Example processing endpoint
    return {"received_data": item.data, "processed": True}