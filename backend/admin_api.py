"""Admin API endpoints for Ixora AI Assistant."""

import os
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.database import get_db
from database.models import ChatSession, ChatMessage, AdminUser
from database.chat_logger import ChatLogger
from admin.auth import (
    authenticate_admin,
    create_access_token,
    get_current_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Create router
router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models
class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class ChatSessionResponse(BaseModel):
    """Chat session response model."""
    id: str
    created_at: str
    updated_at: str
    agent_mode: Optional[str]
    booking_completed: bool
    message_count: int


class ChatMessageResponse(BaseModel):
    """Chat message response model."""
    id: int
    role: str
    content: str
    timestamp: str
    agent_mode: Optional[str]


class AnalyticsResponse(BaseModel):
    """Analytics response model."""
    total_sessions: int
    total_messages: int
    rag_sessions: int
    booking_sessions: int
    completed_bookings: int


# Authentication endpoints
@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint.

    Args:
        form_data: OAuth2 password form (username, password)
        db: Database session

    Returns:
        Access token
    """
    admin = authenticate_admin(db, form_data.username, form_data.password)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.username},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_current_user(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Get current admin user info.

    Args:
        current_admin: Current authenticated admin

    Returns:
        Admin user info
    """
    return current_admin.to_dict()


# Chat log endpoints
@router.get("/chats", response_model=List[ChatSessionResponse])
async def get_all_chats(
    limit: int = 100,
    offset: int = 0,
    agent_mode: Optional[str] = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all chat sessions.

    Args:
        limit: Maximum number of sessions
        offset: Number of sessions to skip
        agent_mode: Filter by agent mode
        current_admin: Current authenticated admin
        db: Database session

    Returns:
        List of chat sessions
    """
    with ChatLogger(db) as logger:
        sessions = logger.get_all_sessions(limit=limit, offset=offset, agent_mode=agent_mode)

    return [
        ChatSessionResponse(
            id=s.id,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            agent_mode=s.agent_mode,
            booking_completed=s.booking_completed or False,
            message_count=len(s.messages)
        )
        for s in sessions
    ]


@router.get("/chats/{session_id}")
async def get_chat_detail(
    session_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed chat session with all messages.

    Args:
        session_id: Session ID
        current_admin: Current authenticated admin
        db: Database session

    Returns:
        Chat session with messages
    """
    with ChatLogger(db) as logger:
        session = logger.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        messages = logger.get_session_messages(session_id)

    return {
        "session": session.to_dict(),
        "messages": [
            ChatMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp.isoformat(),
                agent_mode=m.agent_mode
            )
            for m in messages
        ]
    }


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get analytics and statistics.

    Args:
        current_admin: Current authenticated admin
        db: Database session

    Returns:
        Analytics data
    """
    total_sessions = db.query(ChatSession).count()
    total_messages = db.query(ChatMessage).count()

    rag_sessions = db.query(ChatSession).filter(ChatSession.agent_mode == "rag").count()
    booking_sessions = db.query(ChatSession).filter(
        ChatSession.agent_mode.in_(["booking", "mixed"])
    ).count()

    completed_bookings = db.query(ChatSession).filter(
        ChatSession.booking_completed == True
    ).count()

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_messages=total_messages,
        rag_sessions=rag_sessions,
        booking_sessions=booking_sessions,
        completed_bookings=completed_bookings
    )


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Upload a new document for RAG.

    Args:
        file: PDF file to upload
        current_admin: Current authenticated admin

    Returns:
        Upload status
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # Create documents directory if it doesn't exist
    docs_dir = "documents"
    os.makedirs(docs_dir, exist_ok=True)

    # Save file
    file_path = os.path.join(docs_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "message": "Document uploaded successfully",
        "filename": file.filename,
        "path": file_path,
        "note": "Run the re-index command to update the vector store"
    }


@router.post("/documents/reindex")
async def reindex_documents(
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Re-index all documents in the vector store.

    Args:
        current_admin: Current authenticated admin

    Returns:
        Re-index status
    """
    try:
        from rag.document_loader import load_and_chunk_documents
        from rag.vector_store import initialize_vector_store

        # Get all PDFs from documents directory
        docs_dir = "documents"
        if not os.path.exists(docs_dir):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documents directory not found"
            )

        # Load and chunk documents
        chunks = load_and_chunk_documents(directory_path=docs_dir)

        # Re-initialize vector store
        vector_store = initialize_vector_store(
            documents=chunks,
            force_recreate=True
        )

        return {
            "message": "Documents re-indexed successfully",
            "total_chunks": len(chunks)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error re-indexing documents: {str(e)}"
        )


@router.delete("/chats/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a chat session and all its messages.

    Args:
        session_id: Session ID to delete
        current_admin: Current authenticated admin
        db: Database session

    Returns:
        Deletion status
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    db.delete(session)
    db.commit()

    return {
        "message": "Session deleted successfully",
        "session_id": session_id
    }
