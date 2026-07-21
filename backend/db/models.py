"""Database models for AI Content OS"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    create_engine, Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.config import get_config

Base = declarative_base()

engine = None
SessionLocal = None


def init_db(database_url: Optional[str] = None):
    global engine, SessionLocal
    config = get_config()
    url = database_url or config.database.url

    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=config.database.echo
        )
    else:
        engine = create_engine(
            url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            echo=config.database.echo
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


def get_db():
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    if engine is None:
        init_db()
    Base.metadata.create_all(bind=engine)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="member")
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(512), nullable=True)
    preferences = Column(JSON, default=dict)

    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="user")


class APIKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    permissions = Column(JSON, default=list)

    user = relationship("User", back_populates="api_keys")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")
    settings = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)

    owner = relationship("User", back_populates="projects")
    contents = relationship("Content", back_populates="project")
    workflows = relationship("Workflow", back_populates="project")
    brands = relationship("Brand", back_populates="project")


class Content(Base, TimestampMixin):
    __tablename__ = "contents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False)
    body = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    word_count = Column(Integer, default=0)
    language = Column(String(10), default="en")
    tags = Column(JSON, default=list)
    seo_data = Column(JSON, default=dict)
    brand_id = Column(String(36), ForeignKey("brands.id"), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    published_at = Column(DateTime, nullable=True)
    publish_url = Column(String(1024), nullable=True)

    project = relationship("Project", back_populates="contents")
    brand = relationship("Brand", back_populates="contents")
    revisions = relationship("ContentRevision", back_populates="content")
    analytics = relationship("ContentAnalytics", back_populates="content")

    __table_args__ = (
        Index("idx_content_project_type", "project_id", "content_type"),
        Index("idx_content_status", "status"),
    )


class ContentRevision(Base, TimestampMixin):
    __tablename__ = "content_revisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    content_id = Column(String(36), ForeignKey("contents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    change_summary = Column(Text, nullable=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    content = relationship("Content", back_populates="revisions")


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    voice_tone = Column(String(255), nullable=True)
    target_audience = Column(Text, nullable=True)
    keywords = Column(JSON, default=list)
    style_guide = Column(JSON, default=dict)
    color_palette = Column(JSON, default=list)
    logo_url = Column(String(512), nullable=True)
    guidelines = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    project = relationship("Project", back_populates="brands")
    contents = relationship("Content", back_populates="brand")
    memories = relationship("Memory", back_populates="brand")


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")
    definition = Column(JSON, nullable=False, default=dict)
    schedule = Column(JSON, nullable=True)
    trigger_type = Column(String(50), default="manual")
    metadata_ = Column("metadata", JSON, default=dict)

    project = relationship("Project", back_populates="workflows")
    runs = relationship("WorkflowRun", back_populates="workflow")


class WorkflowRun(Base, TimestampMixin):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    step_results = Column(JSON, default=dict)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    duration_seconds = Column(Float, nullable=True)

    workflow = relationship("Workflow", back_populates="runs")

    __table_args__ = (
        Index("idx_workflow_run_status", "status"),
    )


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    brand_id = Column(String(36), ForeignKey("brands.id"), nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    memory_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    embedding_id = Column(String(255), nullable=True)
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    expires_at = Column(DateTime, nullable=True)

    brand = relationship("Brand", back_populates="memories")

    __table_args__ = (
        Index("idx_memory_type", "memory_type"),
        Index("idx_memory_user_project", "user_id", "project_id"),
    )


class Plugin(Base, TimestampMixin):
    __tablename__ = "plugins"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    plugin_type = Column(String(50), nullable=False)
    is_enabled = Column(Boolean, default=True)
    config = Column(JSON, default=dict)
    metadata_ = Column("metadata", JSON, default=dict)


class ContentAnalytics(Base, TimestampMixin):
    __tablename__ = "content_analytics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    content_id = Column(String(36), ForeignKey("contents.id"), nullable=False)
    metric_type = Column(String(50), nullable=False)
    metric_value = Column(Float, nullable=False)
    source = Column(String(100), nullable=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    content = relationship("Content", back_populates="analytics")

    __table_args__ = (
        Index("idx_analytics_content_metric", "content_id", "metric_type"),
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(36), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


class UsageRecord(Base, TimestampMixin):
    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    model_provider = Column(String(100), nullable=False)
    model_name = Column(String(255), nullable=False)
    operation = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    __table_args__ = (
        Index("idx_usage_user_project", "user_id", "project_id"),
        Index("idx_usage_model", "model_provider", "model_name"),
    )
