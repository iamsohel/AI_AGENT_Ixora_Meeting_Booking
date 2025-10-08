"""FastAPI application for Ixora Meeting Booking Agent."""

import os
import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.graph import BookingAgent

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Ixora Meeting Booking API",
    description="AI-powered meeting booking assistant API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions: Dict[str, Dict] = {}

# Session cleanup configuration
SESSION_TIMEOUT_MINUTES = 30


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str
    session_id: str
    timestamp: str


class SessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    message: str


def cleanup_old_sessions():
    """Remove sessions older than SESSION_TIMEOUT_MINUTES."""
    cutoff_time = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    expired_sessions = [
        sid for sid, data in sessions.items()
        if data.get("last_activity", datetime.now()) < cutoff_time
    ]
    for sid in expired_sessions:
        del sessions[sid]


def get_or_create_agent(session_id: str) -> BookingAgent:
    """Get existing agent for session or create new one."""
    cleanup_old_sessions()

    if session_id not in sessions:
        # Create new agent
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        agent = BookingAgent(llm)
        agent.initialize_state()

        sessions[session_id] = {
            "agent": agent,
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
    else:
        # Update last activity
        sessions[session_id]["last_activity"] = datetime.now()

    return sessions[session_id]["agent"]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Ixora Meeting Booking API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions)
    }


@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())

    # Initialize agent for this session
    get_or_create_agent(session_id)

    return SessionResponse(
        session_id=session_id,
        message="Session created successfully"
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest = Body(...)):
    """
    Send a message to the booking agent and get a response.

    Args:
        request: ChatRequest with message and optional session_id

    Returns:
        ChatResponse with agent's reply and session_id
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Get or create agent for this session
        agent = get_or_create_agent(session_id)

        # Process message
        response_message = agent.process_message(request.message)

        return ChatResponse(
            message=response_message,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@app.post("/api/reset")
async def reset_session(session_id: str = Body(..., embed=True)):
    """
    Reset a chat session.

    Args:
        session_id: The session ID to reset

    Returns:
        Success message
    """
    if session_id in sessions:
        # Reset the agent state
        agent = sessions[session_id]["agent"]
        agent.reset()
        agent.initialize_state()

        sessions[session_id]["last_activity"] = datetime.now()

        return {
            "message": "Session reset successfully",
            "session_id": session_id
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a chat session.

    Args:
        session_id: The session ID to delete

    Returns:
        Success message
    """
    if session_id in sessions:
        del sessions[session_id]
        return {
            "message": "Session deleted successfully",
            "session_id": session_id
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )


@app.get("/api/stats")
async def get_stats():
    """Get API statistics."""
    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "created_at": data["created_at"].isoformat(),
                "last_activity": data["last_activity"].isoformat()
            }
            for sid, data in sessions.items()
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # Validate environment
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY not set in environment")
    if not os.getenv("IXORA_BOOKING_URL"):
        raise ValueError("IXORA_BOOKING_URL not set in environment")

    print("\n🚀 Starting Ixora Meeting Booking API...")
    print(f"📍 API URL: http://localhost:8000")
    print(f"📖 Docs: http://localhost:8000/docs")
    print(f"🔍 Health: http://localhost:8000/api/health\n")

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
