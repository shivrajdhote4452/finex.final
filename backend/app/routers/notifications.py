"""Notifications API Router.

Task ID: S6-API-03
Author: Shivraj Dhote
Date: 16 October 2026

Exposes:
- GET /notifications: List notifications with pagination and unread counts
- GET /notifications/unread-count: Return count of unread notifications
- PATCH /notifications/{notification_id}/read: Mark single notification read
- POST /notifications/mark-all-read: Mark all unread notifications read
- GET /notifications/{notification_id}/delivery: View delivery attempt audit records
"""

from backend.app.core.envelope import create_response_envelope
from backend.app.domain.notifications_service import NotificationsService
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

router = APIRouter(prefix="/notifications", tags=["Notification Center"])
notifications_service = NotificationsService()


@router.get("")
async def list_notifications(
    request: Request,
    unread_only: bool = Query(False, description="Filter for unread messages only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_id),
):
    """Retrieve owner-scoped notifications."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    result = notifications_service.list_notifications(user_id, unread_only=unread_only, limit=limit, offset=offset)
    return create_response_envelope(data=result, correlation_id=cid)


@router.get("/unread-count")
async def get_unread_notification_count(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Get fast badge unread counter for notification bell."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    count = notifications_service.get_unread_count(user_id)
    return create_response_envelope(data={"unread_count": count}, correlation_id=cid)


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Mark a notification as read with ownership enforcement."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        updated = notifications_service.mark_as_read(user_id, notification_id)
        return create_response_envelope(data=updated, correlation_id=cid)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found or access denied.",
        )


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Mark all unread notifications for current user as read."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    count = notifications_service.mark_all_as_read(user_id)
    return create_response_envelope(data={"marked_read_count": count}, correlation_id=cid)


@router.get("/{notification_id}/delivery")
async def get_notification_delivery_attempts(
    notification_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Audit delivery attempts across channels for a specific notification."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        attempts = notifications_service.get_delivery_attempts(user_id, notification_id)
        return create_response_envelope(
            data={"notification_id": notification_id, "attempts": attempts},
            correlation_id=cid,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found or access denied.",
        )
