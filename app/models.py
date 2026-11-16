"""Persistent requests, quarantine records, feedback, and run outcomes."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    claim_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    workflow_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    run_latency_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

class QuarantinedRequest(Base):
    __tablename__ = "quarantined_requests"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    client_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    field_errors_json: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

class Feedback(Base):
    __tablename__ = "claim_feedback"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    satisfactory: Mapped[bool] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
"""Persisted quality monitoring observations for sampled completed runs."""
from datetime import datetime,timezone
from sqlalchemy import DateTime,String,Float,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class QualityScore(Base):
    __tablename__="quality_scores"
    id:Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    run_id:Mapped[str]=mapped_column(String(36),index=True,nullable=False)
    scored_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
    groundedness:Mapped[float]=mapped_column(Float,nullable=False)
    context_relevance:Mapped[float]=mapped_column(Float,nullable=False)
    faithfulness:Mapped[float]=mapped_column(Float,nullable=False)
    hallucination_rate:Mapped[float]=mapped_column(Float,nullable=False)
    method:Mapped[str]=mapped_column(String(40),default="live_proxy_v1",nullable=False)
    detail_json:Mapped[str]=mapped_column(Text,default="{}",nullable=False)
