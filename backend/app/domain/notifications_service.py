"""Notifications Service and Delivery Status Tracking.

Task ID: S6-API-03
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. In-app notification center (list, unread count, mark read, mark all read).
2. Strict user isolation: users can only view and update their own notifications.
3. Delivery attempt audit tracking (in-app, push, email).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.app.domain.alerts_service import (
    _DELIVERY_ATTEMPTS_STORE,
    _NOTIFICATIONS_STORE,
)


class NotificationsService:
    """Manages user notifications with strict ownership verification."""

    def list_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        user_notifs = [
            n
            for n in _NOTIFICATIONS_STORE.values()
            if n["user_id"] == user_id and (not unread_only or not n["is_read"])
        ]
        user_notifs.sort(key=lambda x: x["created_at"], reverse=True)
        total_count = len(user_notifs)
        paginated = user_notifs[offset : offset + limit]

        # Attach delivery attempt summary to each notification
        enriched = []
        for n in paginated:
            attempts = _DELIVERY_ATTEMPTS_STORE.get(n["id"], [])
            item = dict(n)
            item["delivery_attempts_count"] = len(attempts)
            item["last_delivery_channel"] = attempts[-1]["channel"] if attempts else "IN_APP"
            item["last_delivery_status"] = attempts[-1]["attempt_status"] if attempts else "SUCCESS"
            enriched.append(item)

        unread_count = sum(1 for n in _NOTIFICATIONS_STORE.values() if n["user_id"] == user_id and not n["is_read"])

        return {
            "total": total_count,
            "unread_count": unread_count,
            "notifications": enriched,
        }

    def get_unread_count(self, user_id: str) -> int:
        return sum(1 for n in _NOTIFICATIONS_STORE.values() if n["user_id"] == user_id and not n["is_read"])

    def mark_as_read(self, user_id: str, notification_id: str) -> Dict[str, Any]:
        notif = _NOTIFICATIONS_STORE.get(notification_id)
        if not notif or notif["user_id"] != user_id:
            raise KeyError(f"Notification {notification_id} not found or access denied.")

        notif["is_read"] = True
        notif["read_at"] = datetime.now(timezone.utc).isoformat()
        _NOTIFICATIONS_STORE[notification_id] = notif
        return notif

    def mark_all_as_read(self, user_id: str) -> int:
        count = 0
        now_str = datetime.now(timezone.utc).isoformat()
        for notif in _NOTIFICATIONS_STORE.values():
            if notif["user_id"] == user_id and not notif["is_read"]:
                notif["is_read"] = True
                notif["read_at"] = now_str
                count += 1
        return count

    def get_delivery_attempts(self, user_id: str, notification_id: str) -> List[Dict[str, Any]]:
        notif = _NOTIFICATIONS_STORE.get(notification_id)
        if not notif or notif["user_id"] != user_id:
            raise KeyError(f"Notification {notification_id} not found or access denied.")
        return _DELIVERY_ATTEMPTS_STORE.get(notification_id, [])
