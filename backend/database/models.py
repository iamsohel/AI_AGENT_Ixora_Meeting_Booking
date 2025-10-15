"""SQLAlchemy models for chat logging and admin management."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ChatSession(Base):
    """Chat session model - represents a conversation."""

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    agent_mode = Column(String, nullable=True)  # "rag", "booking", or "mixed"

    # Booking-specific fields (if applicable)
    booking_completed = Column(Boolean, default=False)
    booking_date = Column(String, nullable=True)
    booking_time = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    user_email = Column(String, nullable=True)
    user_phone = Column(String, nullable=True)

    # Relationship
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_ip": self.user_ip,
            "agent_mode": self.agent_mode,
            "booking_completed": self.booking_completed,
            "booking_date": self.booking_date,
            "booking_time": self.booking_time,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "user_phone": self.user_phone,
            "message_count": len(self.messages) if self.messages else 0
        }


class ChatMessage(Base):
    """Chat message model - individual messages in a conversation."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Metadata
    agent_mode = Column(String, nullable=True)  # Which agent handled this (rag/booking)
    intent_classification = Column(JSON, nullable=True)  # Classification metadata
    rag_sources = Column(JSON, nullable=True)  # RAG source documents

    # Relationship
    session = relationship("ChatSession", back_populates="messages")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "agent_mode": self.agent_mode,
            "intent_classification": self.intent_classification,
            "rag_sources": self.rag_sources
        }


class AdminUser(Base):
    """Admin user model for authentication."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    def to_dict(self):
        """Convert to dictionary (excluding password)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
