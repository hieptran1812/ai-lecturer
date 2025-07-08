from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import json
import uuid
from typing import Dict, List
import logging

from backend.config import settings
from backend.models.schemas import (
    ChatMessage,
    StudentProfile,
    TTSRequest,
    STTResponse,
)

from backend.agents.ai_teacher import get_ai_teacher
from backend.services.tts_service import get_tts_service
from backend.services.stt_service import get_stt_service
from backend.utils.document_processor import DocumentProcessor
from backend.utils.session_manager import SessionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Teacher Backend",
    description="Backend service for AI English Teacher system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
document_processor = DocumentProcessor()
session_manager = SessionManager()

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@app.get("/")
async def root():
    """
    Health check endpoint
    """
    return {"message": "AI Teacher Backend is running", "version": "1.0.0"}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process educational document
    """
    try:
        logger.info(
            f"Uploading file: {file.filename}, content_type: {file.content_type}"
        )

        if not file.filename or not file.filename.endswith(
            tuple(settings.allowed_file_types)
        ):
            raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed types: {settings.allowed_file_types}",
            )

        # Read file content first to check size
        content = await file.read()

        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.max_file_size} bytes",
            )

        logger.info(f"File size: {len(content)} bytes")

        # Process document
        processed_doc = await document_processor.process_file(
            filename=file.filename,
            content=content,
            file_type=file.content_type or "text/plain",
        )

        logger.info(f"Document processed successfully: {processed_doc['document_id']}")

        # Generate lesson plan using AI teacher
        ai_teacher = get_ai_teacher()
        lesson_plan = await ai_teacher.process_document(
            processed_doc["content"], processed_doc["type"]
        )

        logger.info("Lesson plan generated successfully")

        return {
            "document_id": processed_doc["document_id"],
            "filename": file.filename,
            "lesson_plan": lesson_plan,
            "status": "processed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to process document: {str(e)}"
        )


@app.post("/api/sessions/create")
async def create_session(document_id: str, student_profile: StudentProfile):
    """
    Create new lesson session
    """
    try:
        session = session_manager.create_session(document_id, student_profile)
        return {"session_id": session.session_id, "status": "created"}

    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get session details
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except Exception as e:
        logger.error(f"Get session error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/summary")
async def get_session_summary(session_id: str):
    """
    Generate session summary and feedback
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        student_profile = session_manager.get_student_profile(session.student_id)
        ai_teacher = get_ai_teacher()

        summary = await ai_teacher.generate_session_summary(session, student_profile)

        return summary

    except Exception as e:
        logger.error(f"Session summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts/synthesize")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech
    """
    try:
        tts_service = get_tts_service()
        audio_base64 = tts_service.text_to_speech_base64(request.text, request.language)

        return {
            "audio_data": audio_base64,
            "format": "wav",
            "language": request.language,
        }

    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stt/transcribe")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Convert speech to text
    """
    try:
        audio_data = await file.read()
        stt_service = get_stt_service()

        text, confidence = stt_service.transcribe_audio_file(audio_data)

        return STTResponse(
            transcribed_text=text, confidence=confidence, language="en-US"
        )

    except Exception as e:
        logger.error(f"STT error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat with AI teacher
    """
    await websocket.accept()
    active_connections[session_id] = websocket

    try:
        # Get session and student profile
        session = session_manager.get_session(session_id)
        if not session:
            await websocket.send_text(json.dumps({"error": "Session not found"}))
            return

        student_profile = session_manager.get_student_profile(session.student_id)
        ai_teacher = get_ai_teacher()

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["type"] == "chat":
                user_message = message_data["content"]

                # Add user message to session
                user_chat = ChatMessage(role="user", content=user_message)
                session_manager.add_message(session_id, user_chat)

                # Get lesson context
                lesson_context = session_manager.get_lesson_context(session_id)

                # Generate AI response
                ai_response = await ai_teacher.generate_response(
                    user_message, lesson_context, student_profile, session.messages
                )

                # Add AI message to session
                ai_chat = ChatMessage(role="assistant", content=ai_response["message"])
                session_manager.add_message(session_id, ai_chat)

                # Update session with learning notes
                if ai_response.get("vocabulary_items"):
                    session_manager.add_vocabulary_notes(
                        session_id, ai_response["vocabulary_items"]
                    )

                if ai_response.get("grammar_notes"):
                    session_manager.add_grammar_notes(
                        session_id, ai_response["grammar_notes"]
                    )

                # Send response back to client
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "chat_response",
                            "content": ai_response["message"],
                            "vocabulary": ai_response.get("vocabulary_items", []),
                            "grammar": ai_response.get("grammar_notes", []),
                            "timestamp": ai_response["timestamp"].isoformat(),
                        }
                    )
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
        if session_id in active_connections:
            del active_connections[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_text(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )
