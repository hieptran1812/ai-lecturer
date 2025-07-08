#!/usr/bin/env python3
"""
Simple test server for AI Teacher Backend
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import json


# Simple models
class StudentProfile(BaseModel):
    student_id: str
    name: str = "Student"
    level: str = "intermediate"


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


# Initialize FastAPI app
app = FastAPI(
    title="AI Teacher Backend (Simple)",
    description="Simplified backend for testing",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, be more specific
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage
sessions = {}
documents = {}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AI Teacher Backend is running",
        "version": "1.0.0",
        "status": "ok",
    }


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process educational document"""
    try:
        if not file.filename.endswith((".pdf", ".txt", ".docx", ".md")):
            raise HTTPException(status_code=400, detail="File type not supported")

        # Read file content
        content = await file.read()

        # Simple processing (just store the content)
        doc_id = f"doc_{len(documents) + 1}"
        documents[doc_id] = {
            "document_id": doc_id,
            "filename": file.filename,
            "content": content.decode("utf-8", errors="ignore")[
                :1000
            ],  # First 1000 chars
            "size": len(content),
        }

        return {
            "document_id": doc_id,
            "filename": file.filename,
            "lesson_plan": {
                "objectives": ["Learn from uploaded document"],
                "vocabulary": ["example", "learning", "education"],
                "grammar": ["present tense", "simple sentences"],
            },
            "status": "processed",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/create")
async def create_session(document_id: str, student_profile: StudentProfile):
    """Create new lesson session"""
    try:
        if document_id not in documents:
            raise HTTPException(status_code=404, detail="Document not found")

        session_id = f"session_{len(sessions) + 1}"
        sessions[session_id] = {
            "session_id": session_id,
            "document_id": document_id,
            "student_id": student_profile.student_id,
            "messages": [],
            "created": True,
        }

        return {"session_id": session_id, "status": "created"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return sessions[session_id]


@app.post("/api/tts/synthesize")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech (mock response)"""
    try:
        # Mock response - in real implementation would generate actual audio
        mock_audio_data = "UklGRnoGAABXQVZFZm10IBAAAAABAAEA"  # Mock base64 audio

        return {
            "audio_data": mock_audio_data,
            "format": "wav",
            "language": request.language,
            "message": f"TTS for: {request.text[:50]}...",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stt/transcribe")
async def speech_to_text(file: UploadFile = File(...)):
    """Convert speech to text (mock response)"""
    try:
        # Mock response - in real implementation would transcribe actual audio
        return {
            "transcribed_text": "Hello, this is a mock transcription",
            "confidence": 0.95,
            "language": "en-US",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("🎓 Starting AI Teacher Simple Backend...")
    uvicorn.run(
        "test_server:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
