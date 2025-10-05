from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class Item(BaseModel):
    """
    Pydantic model for an item in a ticket.
    """
    description: str
    price: float


class TicketCreate(BaseModel):
    """
    Pydantic model for creating a ticket.
    """
    merchant_name: str
    transaction_date: Optional[date] = None
    total_amount: float
    category: str
    items: List[Item]
    token_count: Optional[int] = 0


class TicketResponse(TicketCreate):
    """
    Pydantic model for ticket create response.
    """
    id: int
    s3_path: str
    user_id: str

    class Config:
        orm_mode = True


class TicketApproveVerifyRequest(BaseModel):
    """
    Pydantic model for request for approving or verifying a ticket.
    """
    id: int


class TicketApproveVerifyResponse(BaseModel):
    """
    Pydantic model for the response after approving or verifying a ticket.
    """
    id: int
    status: str
