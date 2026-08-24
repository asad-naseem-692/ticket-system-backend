import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentResponse

router = APIRouter(tags=["Attachments"])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "pdf",
    "txt", "csv", "docx", "xlsx", "zip", "json", "log"
}

@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an attachment linked to a ticket",
)
async def upload_attachment(
    ticket_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts and securely stores an attachment linked to a ticket (FEAT-25):
    - Validates file size (max 10MB) and allowed extensions.
    - Stores file on disk under unique filename.
    - Saves metadata in attachments table.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # RBAC check
    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to attach files to this ticket.",
        )
    elif current_user.role == "agent" and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: this ticket is not assigned to your queue.",
        )

    # Extension validation
    original_filename = file.filename or "attachment"
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read and validate size
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({round(file_size / (1024*1024), 2)}MB) exceeds maximum limit of 10MB.",
        )

    # Save to disk with deterministic filename
    attachment_id = str(uuid.uuid4())
    stored_filename = f"{attachment_id}_{original_filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Save record
    new_attachment = Attachment(
        id=attachment_id,
        ticket_id=ticket.id,
        uploaded_by=current_user.id,
        filename=original_filename,
        url=f"/attachments/{attachment_id}",
        size_bytes=file_size,
    )

    db.add(new_attachment)
    db.commit()
    db.refresh(new_attachment)

    return new_attachment

@router.get(
    "/tickets/{ticket_id}/attachments",
    response_model=List[AttachmentResponse],
    summary="List all attachments for a ticket",
)
def list_ticket_attachments(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all attachments linked to a ticket (FEAT-26).
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
            detail="You do not have permission to view attachments for this ticket.",
        )
    elif current_user.role == "agent" and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: this ticket is not assigned to your queue.",
        )

    attachments = (
        db.query(Attachment)
        .options(joinedload(Attachment.uploader))
        .filter(Attachment.ticket_id == ticket_id)
        .order_by(Attachment.created_at.asc())
        .all()
    )
    return attachments

@router.get(
    "/attachments/{attachment_id}",
    summary="Download / view an attachment file",
)
def download_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Streams the attachment file securely with ticket permission checks (FEAT-26).
    """
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    ticket = db.query(Ticket).filter(Ticket.id == attachment.ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent ticket not found",
        )

    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to download this attachment.",
        )
    elif current_user.role == "agent" and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: this ticket is not assigned to your queue.",
        )

    # Locate file on disk
    stored_filename = f"{attachment.id}_{attachment.filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file was not found on server disk.",
        )

    return FileResponse(
        path=file_path,
        filename=attachment.filename,
        media_type="application/octet-stream",
    )
