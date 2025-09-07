from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class Item(BaseModel):
    description: str
    price: float

class TicketCreate(BaseModel):
    merchant_name: str
    transaction_date: date
    total_amount: float
    category: str
    items: List[Item]

class TicketResponse(TicketCreate):
    id: int
    s3_path: str
    user_id: str

    class Config:
        orm_mode = True