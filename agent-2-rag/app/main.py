# Basic FastAPI application
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Agent 2 - RAG")

class Item(BaseModel):
    data: str

@app.get("/")
def read_root():
    # Health check endpoint
    return {"status": "ok", "service": "Agent 2 - RAG"}

@app.post("/process")
def process_data(item: Item):
    # Example processing endpoint
    return {"received_data": item.data, "processed": True}