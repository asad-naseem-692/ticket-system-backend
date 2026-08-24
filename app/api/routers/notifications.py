from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse
from app.services.sla_monitor import check_sla_breaches_and_warnings

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get(
    "",
    response_model=List[NotificationResponse],
    summary="Get notifications for the current user",
)
def get_my_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns notifications and SLA breach/warning alerts for the logged-in user (FEAT-29).
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.read == False)

    notifications = query.order_by(Notification.created_at.desc()).all()
    return notifications

@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks an individual alert/notification as read.
    """
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notif.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot update another user's notifications.",
        )

    notif.read = True
    db.commit()
    db.refresh(notif)

    return notif

@router.post(
    "/read-all",
    summary="Mark all notifications as read",
)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks all notifications for the authenticated user as read.
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False,
    ).update({"read": True}, synchronize_session=False)

    db.commit()
    return {"message": "All notifications marked as read."}

@router.post(
    "/sla-check",
    summary="Trigger immediate SLA breach & warning check",
)
def trigger_sla_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Triggers an immediate SLA calculation and notification dispatch (staff only).
    """
    if current_user.role not in ["agent", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to support staff",
        )

    result = check_sla_breaches_and_warnings(db)
    return result
