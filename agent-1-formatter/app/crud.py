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
        user_id=user_id,
        need_verify=False,
        approved=False,
        token_count=ticket_data.token_count
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def approve_ticket(db: Session, id: int, user_id: str):
    db_ticket = db.query(models.Ticket).filter(models.Ticket.id == id, models.Ticket.user_id == user_id).first()
    if not db_ticket:
        return None
    if db_ticket.need_verify:
        raise ValueError("Ticket requires verification, cannot approve directly.")
    db_ticket.approved = True
    db.commit()
    return db_ticket


def verify_ticket(db: Session, id: int, user_id: str):
    db_ticket = db.query(models.Ticket).filter(models.Ticket.id == id, models.Ticket.user_id == user_id).first()
    if not db_ticket:
        return None
    if db_ticket.approved:
        raise ValueError("Ticket already approved.")
    db_ticket.need_verify = True
    db.commit()
    return db_ticket


def get_user_tickets(db: Session, user_id: str, limit: int = 10, need_verify: bool = None):
    """Get recent tickets for a user"""
    # For admin users, show all tickets
    # For regular users, filter by user_id
    query = db.query(models.Ticket)

    # Filter by need_verify if specified
    if need_verify is not None:
        query = query.filter(models.Ticket.need_verify == need_verify)
        # Also exclude tickets that already have ground truth
        query = query.filter(models.Ticket.has_ground_truth == False)

    tickets = query.order_by(models.Ticket.id.desc()).limit(limit).all()
    return tickets


def save_ground_truth(
    db: Session,
    ticket_id: int,
    corrected_merchant: str,
    corrected_date: str,
    corrected_amount: float,
    corrected_items: list,
    corrected_by: str
):
    """Save ground truth for a ticket and mark it as approved"""
    from sqlalchemy import text

    # Insert ground truth
    db.execute(
        text("""
            INSERT INTO ticket_ground_truth
            (ticket_id, corrected_merchant, corrected_date, corrected_amount, corrected_items, corrected_by)
            VALUES (:ticket_id, :merchant, :date, :amount, :items, :corrected_by)
            ON CONFLICT (ticket_id) DO UPDATE SET
                corrected_merchant = :merchant,
                corrected_date = :date,
                corrected_amount = :amount,
                corrected_items = :items,
                corrected_by = :corrected_by
        """),
        {
            "ticket_id": ticket_id,
            "merchant": corrected_merchant,
            "date": corrected_date,
            "amount": corrected_amount,
            "items": corrected_items,
            "corrected_by": corrected_by
        }
    )

    # Update ticket to mark as approved and has_ground_truth
    db.execute(
        text("""
            UPDATE tickets
            SET approved = TRUE, has_ground_truth = TRUE
            WHERE id = :ticket_id
        """),
        {"ticket_id": ticket_id}
    )

    db.commit()