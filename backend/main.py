"""FastAPI application for Ixora Meeting Booking Agent."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import admin_api
from agent.unified_agent import UnifiedAgent
from database.chat_logger import ChatLogger
from database.database import get_db, init_db
from database.models import ChatSession
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Initialize database on startup
try:
    init_db()
    print("✅ Database initialized")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")

# Configure logging - suppress verbose logs from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize FastAPI app
app = FastAPI(
    title="Ixora AI Assistant API",
    description="AI-powered assistant with RAG (company info) and meeting booking capabilities",
    version="2.0.0",
)

# Path to React build folder
build_path = Path(__file__).parent.parent / "frontend" / "dist"


# Mount static files (JS, CSS, images)
app.mount("/assets", StaticFiles(directory=build_path / "assets"), name="assets")


# Serve index.html for SPA routes
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    index_file = build_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"error": "index.html not found"}


# Include admin router
app.include_router(admin_api.router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev servers and demo.html server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions: Dict[str, Dict] = {}

# Session cleanup configuration
SESSION_TIMEOUT_MINUTES = 300


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
        sid
        for sid, data in sessions.items()
        if data.get("last_activity", datetime.now()) < cutoff_time
    ]
    for sid in expired_sessions:
        del sessions[sid]


def get_or_create_agent(session_id: str) -> UnifiedAgent:
    """Get existing agent for session or create new one."""
    cleanup_old_sessions()

    if session_id not in sessions:
        # Create new agent (RAG + Booking)
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        agent = UnifiedAgent(llm)
        agent.initialize_state()

        sessions[session_id] = {
            "agent": agent,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
        }
    else:
        # Update last activity
        sessions[session_id]["last_activity"] = datetime.now()

    return sessions[session_id]["agent"]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Ixora AI Assistant API",
        "version": "2.0.0",
        "status": "running",
        "capabilities": ["RAG (company info)", "Meeting booking"],
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions),
    }


@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())

    # Initialize agent for this session
    get_or_create_agent(session_id)

    return SessionResponse(
        session_id=session_id, message="Session created successfully"
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest = Body(...), db: Session = Depends(get_db)):
    """
    Send a message to the booking agent and get a response.

    Args:
        request: ChatRequest with message and optional session_id
        db: Database session

    Returns:
        ChatResponse with agent's reply and session_id
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Log user message
        with ChatLogger(db) as logger:
            logger.create_session(session_id)
            logger.log_message(
                session_id=session_id, role="user", content=request.message
            )

        # Get or create agent for this session
        agent = get_or_create_agent(session_id)

        # Process message
        response_message = agent.process_message(request.message)

        # Log assistant response
        with ChatLogger(db) as logger:
            # Get agent mode from state
            agent_mode = agent.state.get("agent_mode") if agent.state else None
            intent_classification = (
                agent.state.get("intent_classification") if agent.state else None
            )
            rag_sources = agent.state.get("rag_sources") if agent.state else None

            logger.log_message(
                session_id=session_id,
                role="assistant",
                content=response_message,
                agent_mode=agent_mode,
                intent_classification=intent_classification,
                rag_sources=rag_sources,
            )

            # Update booking info if applicable
            if agent.state:
                logger.update_session_booking_info(
                    session_id=session_id,
                    booking_completed=agent.state.get("booking_confirmed", False),
                    booking_date=agent.state.get("date_preference"),
                    booking_time=agent.state.get("selected_slot", {}).get("time"),
                    user_name=agent.state.get("user_name"),
                    user_email=agent.state.get("user_email"),
                    user_phone=agent.state.get("user_phone"),
                )

        return ChatResponse(
            message=response_message,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing message: {str(e)}"
        )


async def generate_stream(
    agent: UnifiedAgent, message: str, session_id: str, db: Session = None
):
    """
    Generator function for SSE streaming.

    Yields formatted SSE events with chunks of the agent's response.
    """
    full_response = ""
    try:
        # Process message and get response chunks
        async for item in agent.process_message_stream(message):
            # Check if it's a status update or chunk
            if isinstance(item, dict):
                if item.get("type") == "status":
                    # Send status update
                    event_data = {
                        "status": item.get("message", ""),
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                elif item.get("type") == "chunk":
                    # Accumulate full response for logging
                    chunk_data = item.get("data", "")
                    full_response += chunk_data

                    # Send text chunk
                    event_data = {
                        "chunk": chunk_data,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    continue
            else:
                # Backwards compatibility - treat as chunk
                full_response += str(item)
                event_data = {
                    "chunk": item,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                }

            yield f"data: {json.dumps(event_data)}\n\n"

            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)

        # Log assistant response to database
        if db and full_response:
            with ChatLogger(db) as logger:
                agent_mode = agent.state.get("agent_mode") if agent.state else None
                intent_classification = (
                    agent.state.get("intent_classification") if agent.state else None
                )
                rag_sources = agent.state.get("rag_sources") if agent.state else None

                logger.log_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    agent_mode=agent_mode,
                    intent_classification=intent_classification,
                    rag_sources=rag_sources,
                )

                # Update booking info if applicable
                if agent.state:
                    logger.update_session_booking_info(
                        session_id=session_id,
                        booking_completed=agent.state.get("booking_confirmed", False),
                        booking_date=agent.state.get("date_preference"),
                        booking_time=agent.state.get("selected_slot", {}).get("time"),
                        user_name=agent.state.get("user_name"),
                        user_email=agent.state.get("user_email"),
                        user_phone=agent.state.get("user_phone"),
                    )

        # Send completion event
        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

    except Exception as e:
        # Send error event
        error_data = {"error": str(e), "session_id": session_id}
        yield f"data: {json.dumps(error_data)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest = Body(...), db: Session = Depends(get_db)):
    """
    Send a message to the booking agent and stream the response via SSE.

    Args:
        request: ChatRequest with message and optional session_id
        db: Database session

    Returns:
        StreamingResponse with text/event-stream content
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Log user message to database
        with ChatLogger(db) as logger:
            logger.create_session(session_id)
            logger.log_message(
                session_id=session_id, role="user", content=request.message
            )

        # Get or create agent for this session
        agent = get_or_create_agent(session_id)

        # Return streaming response
        return StreamingResponse(
            generate_stream(agent, request.message, session_id, db),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "X-Frame-Options": "ALLOWALL",
                "Content-Security-Policy": "frame-ancestors *",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing message: {str(e)}"
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

        return {"message": "Session reset successfully", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


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
        return {"message": "Session deleted successfully", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@app.get("/api/stats")
async def get_stats():
    """Get API statistics."""
    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "created_at": data["created_at"].isoformat(),
                "last_activity": data["last_activity"].isoformat(),
            }
            for sid, data in sessions.items()
        ],
    }


if __name__ == "__main__":
    import uvicorn

    # Validate environment
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY not set in environment")
    if not os.getenv("IXORA_BOOKING_URL"):
        raise ValueError("IXORA_BOOKING_URL not set in environment")

    print("\n🚀 Starting Ixora AI Assistant API (RAG + Booking)...")
    print(f"📍 API URL: http://localhost:8000")
    print(f"📖 Docs: http://localhost:8000/docs")
    print(f"🔍 Health: http://localhost:8000/api/health\n")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
