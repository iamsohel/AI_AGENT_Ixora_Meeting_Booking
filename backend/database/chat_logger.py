"""Chat logging utilities."""

from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from .models import ChatSession, ChatMessage
from .database import get_db_session


class ChatLogger:
    """Log chat sessions and messages to database."""

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize chat logger.

        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db
        self._own_session = db is None

    def __enter__(self):
        """Context manager entry."""
        if self._own_session:
            self.db = get_db_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._own_session and self.db:
            self.db.close()

    def create_session(
        self,
        session_id: str,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            session_id: Unique session ID
            user_ip: User's IP address
            user_agent: User's browser user agent

        Returns:
            Created chat session
        """
        # Check if session already exists
        existing = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if existing:
            return existing

        session = ChatSession(
            id=session_id,
            user_ip=user_ip,
            user_agent=user_agent
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def log_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_mode: Optional[str] = None,
        intent_classification: Optional[Dict] = None,
        rag_sources: Optional[List] = None
    ) -> ChatMessage:
        """
        Log a chat message.

        Args:
            session_id: Session ID
            role: Message role ("user" or "assistant")
            content: Message content
            agent_mode: Agent mode ("rag" or "booking")
            intent_classification: Intent classification metadata
            rag_sources: RAG source documents

        Returns:
            Created chat message
        """
        # Ensure session exists
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            session = self.create_session(session_id)

        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            agent_mode=agent_mode,
            intent_classification=intent_classification,
            rag_sources=rag_sources
        )

        self.db.add(message)

        # Update session
        session.updated_at = datetime.utcnow()
        if agent_mode:
            # Track if session used multiple modes
            if session.agent_mode and session.agent_mode != agent_mode:
                session.agent_mode = "mixed"
            else:
                session.agent_mode = agent_mode

        self.db.commit()
        self.db.refresh(message)

        return message

    def update_session_booking_info(
        self,
        session_id: str,
        booking_completed: bool = False,
        booking_date: Optional[str] = None,
        booking_time: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None
    ) -> ChatSession:
        """
        Update session with booking information.

        Args:
            session_id: Session ID
            booking_completed: Whether booking was completed
            booking_date: Booking date
            booking_time: Booking time
            user_name: User's name
            user_email: User's email
            user_phone: User's phone

        Returns:
            Updated chat session
        """
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            session = self.create_session(session_id)

        if booking_completed is not None:
            session.booking_completed = booking_completed
        if booking_date:
            session.booking_date = booking_date
        if booking_time:
            session.booking_time = booking_time
        if user_name:
            session.user_name = user_name
        if user_email:
            session.user_email = user_email
        if user_phone:
            session.user_phone = user_phone

        session.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(session)

        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a chat session by ID.

        Args:
            session_id: Session ID

        Returns:
            Chat session or None
        """
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """
        Get all messages for a session.

        Args:
            session_id: Session ID

        Returns:
            List of chat messages
        """
        return self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp).all()

    def get_all_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_mode: Optional[str] = None
    ) -> List[ChatSession]:
        """
        Get all chat sessions.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            agent_mode: Filter by agent mode

        Returns:
            List of chat sessions
        """
        query = self.db.query(ChatSession)

        if agent_mode:
            query = query.filter(ChatSession.agent_mode == agent_mode)

        return query.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit).all()

    def get_sessions_count(self, agent_mode: Optional[str] = None) -> int:
        """
        Get total number of sessions.

        Args:
            agent_mode: Filter by agent mode

        Returns:
            Total count of sessions
        """
        query = self.db.query(ChatSession)

        if agent_mode:
            query = query.filter(ChatSession.agent_mode == agent_mode)

        return query.count()
