"""Database models for AI Content OS"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    create_engine,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from backend.core.config import get_config


class Base(DeclarativeBase):
    pass


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
            echo=config.database.echo,
        )
    else:
        engine = create_engine(
            url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            echo=config.database.echo,
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(50), default="member")
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    preferences: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner")
    api_keys: Mapped[list["APIKey"]] = relationship("APIKey", back_populates="user")


class APIKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    permissions: Mapped[Optional[list[Any]]] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), default="active")
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    contents: Mapped[list["Content"]] = relationship(
        "Content", back_populates="project"
    )
    workflows: Mapped[list["Workflow"]] = relationship(
        "Workflow", back_populates="project"
    )
    brands: Mapped[list["Brand"]] = relationship("Brand", back_populates="project")


class Content(Base, TimestampMixin):
    __tablename__ = "contents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), default="draft")
    word_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    language: Mapped[Optional[str]] = mapped_column(String(10), default="en")
    tags: Mapped[Optional[list[Any]]] = mapped_column(JSON, default=list)
    seo_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    brand_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("brands.id"), nullable=True
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    publish_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="contents")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="contents")
    revisions: Mapped[list["ContentRevision"]] = relationship(
        "ContentRevision", back_populates="content"
    )
    analytics: Mapped[list["ContentAnalytics"]] = relationship(
        "ContentAnalytics", back_populates="content"
    )

    __table_args__ = (
        Index("idx_content_project_type", "project_id", "content_type"),
        Index("idx_content_status", "status"),
    )


class ContentRevision(Base, TimestampMixin):
    __tablename__ = "content_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )

    content: Mapped["Content"] = relationship("Content", back_populates="revisions")


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_tone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[list[Any]]] = mapped_column(JSON, default=list)
    style_guide: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    color_palette: Mapped[Optional[list[Any]]] = mapped_column(JSON, default=list)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    guidelines: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )

    project: Mapped["Project"] = relationship("Project", back_populates="brands")
    contents: Mapped[list["Content"]] = relationship("Content", back_populates="brand")
    memories: Mapped[list["Memory"]] = relationship("Memory", back_populates="brand")


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), default="active")
    definition: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    schedule: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    trigger_type: Mapped[Optional[str]] = mapped_column(String(50), default="manual")
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )

    project: Mapped["Project"] = relationship("Project", back_populates="workflows")
    runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="workflow"
    )


class WorkflowRun(Base, TimestampMixin):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflows.id"), nullable=False
    )
    status: Mapped[Optional[str]] = mapped_column(String(50), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    step_results: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    input_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")

    __table_args__ = (Index("idx_workflow_run_status", "status"),)


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    brand_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("brands.id"), nullable=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=True
    )
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    importance: Mapped[Optional[float]] = mapped_column(Float, default=0.5)
    access_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="memories")

    __table_args__ = (
        Index("idx_memory_type", "memory_type"),
        Index("idx_memory_user_project", "user_id", "project_id"),
    )


class Plugin(Base, TimestampMixin):
    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plugin_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )


class ContentAnalytics(Base, TimestampMixin):
    __tablename__ = "content_analytics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id"), nullable=False
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )

    content: Mapped["Content"] = relationship("Content", back_populates="analytics")

    __table_args__ = (
        Index("idx_analytics_content_metric", "content_id", "metric_type"),
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


class UsageRecord(Base, TimestampMixin):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=True
    )
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, default=dict
    )

    __table_args__ = (
        Index("idx_usage_user_project", "user_id", "project_id"),
        Index("idx_usage_model", "model_provider", "model_name"),
    )
