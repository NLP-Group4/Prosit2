"""
Platform Database — SQLAlchemy models and engine for the API builder itself.

This is NOT the generated backends' database. This is the platform's own
PostgreSQL database for storing user accounts and project artifacts.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum, Integer,
    create_engine, event, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase, relationship, sessionmaker, Session,
)

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None

# ---------------------------------------------------------------------------
# Database URL — from environment, with fallback for local dev
# ---------------------------------------------------------------------------

PLATFORM_DATABASE_URL = os.getenv(
    "PLATFORM_DATABASE_URL",
    "postgresql://platform:devpassword@localhost:5433/api_builder",
)

engine = create_engine(PLATFORM_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProjectStatus(str, PyEnum):
    PENDING = "pending"
    GENERATING = "generating"
    VERIFYING = "verifying"  # kept for backwards compatibility or Electron usage
    AWAITING_VERIFICATION = "awaiting_verification"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class PlatformUser(Base):
    """User account for the API builder platform."""
    __tablename__ = "platform_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    """A single backend generation run with all its artifacts."""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_name = Column(String(128), nullable=False)
    prompt = Column(Text, nullable=True)
    status = Column(
        Enum(ProjectStatus, name="project_status", create_constraint=True),
        default=ProjectStatus.PENDING,
        nullable=False,
    )
    model_used = Column(String(64), nullable=True)

    # Artifact JSON — persisted at each pipeline step
    spec_json = Column(Text, nullable=True)
    validation_json = Column(Text, nullable=True)
    verification_json = Column(Text, nullable=True)

    # File path (relative to data/ root)
    zip_path = Column(String(512), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    owner = relationship("PlatformUser", back_populates="projects")
    threads = relationship("Thread", back_populates="project", cascade="all, delete-orphan")


class Thread(Base):
    """A conversational session within a Project."""
    __tablename__ = "threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project = relationship("Project", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    """A single chat interaction within a Thread."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(
        UUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False) # "user" or "agent"
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    thread = relationship("Thread", back_populates="messages")


class Document(Base):
    """An uploaded document for RAG context."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA-256 for dedup
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner = relationship("PlatformUser", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """A chunk of a document with its embedding vector."""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )  # Denormalized for fast similarity queries
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768)) if HAS_PGVECTOR else Column(Text)  # pgvector

    # Relationship
    document = relationship("Document", back_populates="chunks")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db() -> Session:
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create pgvector extension and all tables. Called on application startup."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
