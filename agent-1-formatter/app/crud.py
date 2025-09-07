from sqlalchemy.orm import Session
from . import models, schemas

def create_ticket(db: Session, ticket_data: schemas.TicketCreate, s3_path: str, user_id: str):
    # Convert Pydantic items to a list of dicts for JSON storage
    items_as_dicts = [item.dict() for item in ticket_data.items]

    db_ticket = models.Ticket(
        merchant_name=ticket_data.merchant_name,
        transaction_date=ticket_data.transaction_date,
        total_amount=ticket_data.total_amount,
        category=ticket_data.category,
        items=items_as_dicts,
        s3_path=s3_path,
        user_id=user_id
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket