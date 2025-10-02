from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class Item(BaseModel):
    description: str
    price: float


class TicketCreate(BaseModel):
    merchant_name: str
    transaction_date: Optional[date] = None
    total_amount: float
    category: str
    items: List[Item]
    token_count: Optional[int] = 0


class TicketResponse(TicketCreate):
    id: int
    s3_path: str
    user_id: str

    class Config:
        orm_mode = True


class TicketApproveVerifyRequest(BaseModel):
    id: int


class TicketApproveVerifyResponse(BaseModel):
    id: int
    status: str
