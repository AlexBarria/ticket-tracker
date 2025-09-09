from sqlalchemy import Column, Integer, String, Float, Date, JSON
from .database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    merchant_name = Column(String, index=True)
    transaction_date = Column(Date, nullable=True)
    total_amount = Column(Float)
    category = Column(String, index=True)
    items = Column(JSON) # To store the list of items
    s3_path = Column(String)
    user_id = Column(String, index=True)