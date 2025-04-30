# app/models/api/notification.py
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from app.services import datetime_service as dt


class NotificationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    MS_TEAMS = "MS_TEAMS"
    WEBHOOK = "WEBHOOK"


class Notification(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    external_id: Optional[str] = None
    message: str
    subject: Optional[str] = None
    status: NotificationStatus = NotificationStatus.PENDING
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=dt.now_utc)
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Build failed for commit abc123 on staging.",
                "subject": "Build Alert",
                "status": "PENDING",
                "priority": "HIGH",
                "channel": "SLACK"
            }
        }
    }
