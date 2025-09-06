# Basic FastAPI application
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Agent 1 - Formatter")

class Item(BaseModel):
    data: str

@app.get("/")
def read_root():
    # Health check endpoint
    return {"status": "ok", "service": "Agent 1 - Formatter"}

@app.post("/process")
def process_data(item: Item):
    # Example processing endpoint
    return {"received_data": item.data, "processed": True}