from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["Comments"])

@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or public reply to a ticket",
)
def add_comment(
    ticket_id: str,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new internal note or public reply on a support ticket (FEAT-23, FEAT-24):
    - Public replies (FEAT-24): Allowed by ticket owner (customer), assigned agent, and admin.
    - Internal notes (FEAT-23): Restricted to staff (agent, admin). Customers receive 403 Forbidden.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # 1. Customer permission check
    if current_user.role == "customer":
        if ticket.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to comment on this ticket.",
            )
        if comment_in.visibility == "internal":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers cannot post internal staff notes.",
            )

    # 2. Agent permission check
    elif current_user.role == "agent":
        if ticket.assigned_agent_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only comment on tickets assigned to your queue.",
            )

    # 3. Create comment
    new_comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        visibility=comment_in.visibility,
        content=comment_in.content.strip(),
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return new_comment

@router.get(
    "",
    response_model=List[CommentResponse],
    summary="List comments for a ticket",
)
def list_comments(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns comment history for a ticket (FEAT-23, FEAT-24):
    - Customers only see public comments ('visibility == public' filtered at DB level).
    - Agents & Admins see both public comments and internal staff notes.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view comments for this ticket.",
        )
    elif current_user.role == "agent" and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: this ticket is not assigned to your queue.",
        )

    query = (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.ticket_id == ticket_id)
    )

    # Filter out internal notes for customers at query level
    if current_user.role == "customer":
        query = query.filter(Comment.visibility == "public")

    comments = query.order_by(Comment.created_at.asc()).all()
    return comments
