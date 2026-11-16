"""Validated external API contracts for claims and feedback."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.config import settings

class ClaimSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    complaint: str = Field(min_length=1, max_length=settings.max_complaint_length)
    flight_number: str | None = Field(default=None, max_length=32, pattern=r"^[A-Za-z0-9]{2,3}\s?-?\d{1,4}$")
    disruption_type: Literal["denied boarding", "cancellation", "delay", "downgrading"] | None = None
    scheduled_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    actual_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    alternate_flight: str | None = Field(default=None, max_length=64)
    notice_hours: float | None = Field(default=None, ge=0, le=8760)
    block_time_hours: float | None = Field(default=None, gt=0, le=48)
    contact_details_provided: bool | None = None
    cause_attribution: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def cross_field_rules(self):
        if self.actual_time and not self.scheduled_time:
            raise ValueError("scheduled_time is required when actual_time is supplied")
        return self

class ClaimAccepted(BaseModel):
    claim_id: UUID
    status: Literal["pending"] = "pending"
    message: str = "Claim accepted and pending processing."
    created_at: datetime

ClaimStatus = Literal["pending", "processing", "completed", "failed"]
class ClaimStatusResponse(BaseModel):
    claim_id: UUID
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    failure_message: str | None = None
class ClaimResultResponse(BaseModel):
    claim_id: UUID
    status: Literal["completed"]
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any]
class ClaimFailedResponse(BaseModel):
    claim_id: UUID
    status: Literal["failed"]
    created_at: datetime
    updated_at: datetime
    failure_message: str
class FeedbackSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    satisfactory: bool
    reason: str = Field(min_length=3, max_length=2000)
class FeedbackAccepted(BaseModel):
    feedback_id: int
    claim_id: UUID
    created_at: datetime
class HealthResponse(BaseModel):
    status: str = "ok"
