import sys
from pathlib import Path

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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
from datetime import datetime

from backend.config import settings
from backend.models.schemas import (
    ChatMessage,
    TTSRequest,
    STTResponse,
    SessionCreateRequest,
    SessionSummary,
    StudentProfile,
    LessonSession,
)
from backend.utils.document_processor import DocumentProcessor
from backend.utils.enhanced_document_processor import EnhancedDocumentProcessor
from backend.utils.session_manager import SessionManager
from backend.agents.ai_teacher import get_ai_teacher
from backend.services.stt_service import get_stt_service
from backend.services.tts_service import TTSService, get_tts_service

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
document_processor_config = {
    'max_file_size': settings.max_file_size,
    'max_content_length': settings.max_content_length,
    'extract_key_topics': settings.extract_key_topics,
    'docling': {
        'enable_ocr': settings.docling_ocr_enabled,
        'enable_table_extraction': settings.docling_table_extraction
    }
}

document_processor = DocumentProcessor(document_processor_config)
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
async def create_session(request: SessionCreateRequest):
    """
    Create new lesson session
    """
    try:
        logger.info(f"Creating session with document_id: {request.document_id}")
        logger.info(f"Student profile: {request.student_profile}")

        session = session_manager.create_session(
            request.document_id, request.student_profile
        )

        logger.info(f"Session created successfully: {session.session_id}")
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


@app.get("/api/documents/info")
async def get_document_processing_info():
    """
    Get information about document processing capabilities
    """
    try:
        stats = document_processor.enhanced_processor.get_processing_stats()
        return {
            "supported_types": stats["supported_types"],
            "available_parsers": stats["available_parsers"],
            "max_file_size": stats["max_file_size"],
            "max_content_length": stats["max_content_length"],
            "features": {
                "docling_enabled": settings.docling_enabled,
                "ocr_enabled": settings.docling_ocr_enabled,
                "table_extraction": settings.docling_table_extraction,
                "key_topics_extraction": settings.extract_key_topics
            }
        }
    except Exception as e:
        logger.error("Error getting document processing info: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyze document with enhanced features (structure, tables, images)
    """
    try:
        logger.info("Analyzing document: %s", file.filename)

        if not file.filename or not file.filename.endswith(
            tuple(settings.allowed_file_types)
        ):
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed types: {settings.allowed_file_types}"
            )

        # Read file content
        content = await file.read()

        if len(content) > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
            )

        # Process with enhanced features
        processed_doc = await document_processor.enhanced_processor.process_file(
            filename=file.filename,
            content=content,
            file_type=file.content_type or "text/plain",
            options={
                'extract_topics': True,
                'generate_summary': True
            }
        )

        logger.info("Document analyzed successfully: %s", processed_doc['document_id'])

        return {
            "document_id": processed_doc["document_id"],
            "filename": file.filename,
            "analysis": {
                "content_preview": processed_doc["content"][:500] + "..." if len(processed_doc["content"]) > 500 else processed_doc["content"],
                "metadata": processed_doc["metadata"],
                "structure": processed_doc.get("structure", {}),
                "tables_count": len(processed_doc.get("tables", [])),
                "images_count": len(processed_doc.get("images", [])),
                "key_topics": processed_doc.get("key_topics", []),
                "summary": processed_doc.get("summary", ""),
                "processing_info": processed_doc.get("processing_info", {})
            },
            "status": "analyzed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document analysis error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze document: {str(e)}"
        )


# Docling Service Health Check
@app.get("/api/docling/health")
async def docling_health_check():
    """
    Check Docling service health status
    """
    try:
        from backend.utils.docling_service import get_docling_service
        
        service = get_docling_service()
        health = await service.health_check()
        
        return {
            "status": "success",
            "health": health,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Docling health check failed: %s", str(e))
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/docling/stats")
async def docling_service_stats():
    """
    Get Docling service statistics
    """
    try:
        from backend.utils.docling_service import get_docling_service
        
        service = get_docling_service()
        stats = service.get_service_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get Docling stats: %s", str(e))
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.post("/api/docling/process")
async def process_with_docling(file: UploadFile = File(...)):
    """
    Process document directly with Docling service (advanced processing)
    """
    try:
        from backend.utils.docling_service import get_docling_service
        
        logger.info("Processing document with Docling service: %s", file.filename)
        
        if not file.filename or not file.filename.endswith(tuple(settings.allowed_file_types)):
            raise HTTPException(
                status_code=400,
                detail=f"File type not supported. Allowed types: {settings.allowed_file_types}"
            )
        
        # Read file content
        content = await file.read()
        
        if len(content) > settings.docling_max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large for Docling processing. Maximum size: {settings.docling_max_file_size} bytes"
            )
        
        # Process with Docling service
        service = get_docling_service()
        
        if not service.enabled:
            raise HTTPException(
                status_code=503,
                detail="Docling service is not available"
            )
        
        processed_doc = await service.process_document(
            content=content,
            filename=file.filename,
            options={
                'ocr_enabled': settings.docling_ocr_enabled,
                'table_extraction': settings.docling_table_extraction,
                'processing_mode': settings.docling_processing_mode
            }
        )
        
        logger.info("Document processed successfully with Docling: %s", file.filename)
        
        return {
            "status": "success",
            "document": {
                "filename": file.filename,
                "content": processed_doc.content,
                "metadata": processed_doc.metadata,
                "structure": processed_doc.structure,
                "tables": processed_doc.tables,
                "images": processed_doc.images,
                "processing_info": {
                    "parser_type": "docling_service",
                    "file_size": len(content),
                    "processing_time": processed_doc.metadata.get('processing_time', 0)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Docling processing error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document with Docling: {str(e)}"
        )


@app.post("/api/docling/batch")
async def batch_process_with_docling(files: List[UploadFile] = File(...)):
    """
    Process multiple documents with Docling service
    """
    try:
        from backend.utils.docling_service import get_docling_service
        
        logger.info("Batch processing %d documents with Docling", len(files))
        
        service = get_docling_service()
        
        if not service.enabled:
            raise HTTPException(
                status_code=503,
                detail="Docling service is not available"
            )
        
        # Prepare documents for batch processing
        documents = []
        for file in files:
            if not file.filename or not file.filename.endswith(tuple(settings.allowed_file_types)):
                continue
            
            content = await file.read()
            if len(content) > settings.docling_max_file_size:
                continue
            
            documents.append({
                'content': content,
                'filename': file.filename,
                'options': {
                    'ocr_enabled': settings.docling_ocr_enabled,
                    'table_extraction': settings.docling_table_extraction,
                    'processing_mode': settings.docling_processing_mode
                }
            })
        
        # Process documents
        processed_docs = await service.batch_process_documents(documents)
        
        # Format response
        results = []
        for doc in processed_docs:
            results.append({
                "filename": doc.metadata.get('filename', 'unknown'),
                "content": doc.content,
                "metadata": doc.metadata,
                "structure": doc.structure,
                "tables": doc.tables,
                "images": doc.images
            })
        
        logger.info("Batch processing completed: %d/%d documents processed", 
                   len(results), len(files))
        
        return {
            "status": "success",
            "processed_count": len(results),
            "total_count": len(files),
            "documents": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch processing error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch process documents: {str(e)}"
        )


@app.delete("/api/docling/cache")
async def clear_docling_cache():
    """
    Clear Docling service cache
    """
    try:
        from backend.utils.docling_service import get_docling_service
        
        service = get_docling_service()
        service.clear_cache()
        
        return {
            "status": "success",
            "message": "Docling cache cleared",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to clear Docling cache: %s", str(e))
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )
