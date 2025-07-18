import uuid
from typing import Dict, Optional
from datetime import datetime
import logging

from ..models.schemas import LessonSession, StudentProfile, ChatMessage

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        """
        Initialize session manager
        """
        self.active_sessions: Dict[str, LessonSession] = {}
        self.student_profiles: Dict[str, StudentProfile] = {}
        self.lesson_contexts: Dict[str, Dict] = {}

    def create_session(
        self, document_id: str, student_profile: StudentProfile
    ) -> LessonSession:
        """
        Create a new lesson session

        Args:
            document_id: ID of the document to teach from
            student_profile: Student's profile information

        Returns:
            LessonSession object
        """
        try:
            session_id = str(uuid.uuid4())
            student_id = student_profile.student_id

            # Store student profile
            self.student_profiles[student_id] = student_profile

            # Create session
            session = LessonSession(
                session_id=session_id,
                document_id=document_id,
                student_id=student_id,
                messages=[],
                vocabulary_notes=[],
                grammar_notes=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Store session
            self.active_sessions[session_id] = session

            # Initialize lesson context
            self.lesson_contexts[session_id] = {
                "document_id": document_id,
                "topic": "General English",
                "objectives": [],
                "vocabulary": [],
                "grammar": [],
                "current_focus": "introduction",
            }

            logger.info(f"Created session {session_id} for student {student_id}")
            return session

        except Exception as e:
            logger.error(f"Session creation error: {str(e)}", exc_info=True)
            logger.debug(
                f"Session creation failed for document_id: {document_id}, student_id: {student_profile.student_id}"
            )
            raise Exception(f"Failed to create session: {str(e)}")

    def get_session(self, session_id: str) -> Optional[LessonSession]:
        """
        Get session by ID
        """
        return self.active_sessions.get(session_id)

    def get_student_profile(self, student_id: str) -> Optional[StudentProfile]:
        """
        Get student profile by ID
        """
        return self.student_profiles.get(student_id)

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """
        Add message to session
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id].messages.append(message)
            self.active_sessions[session_id].updated_at = datetime.now()

    def add_vocabulary_notes(self, session_id: str, vocabulary_items: list) -> None:
        """
        Add vocabulary notes to session
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id].vocabulary_notes.extend(vocabulary_items)
            self.active_sessions[session_id].updated_at = datetime.now()

    def add_grammar_notes(self, session_id: str, grammar_items: list) -> None:
        """
        Add grammar notes to session
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id].grammar_notes.extend(grammar_items)
            self.active_sessions[session_id].updated_at = datetime.now()

    def get_lesson_context(self, session_id: str) -> Dict:
        """
        Get lesson context for session
        """
        return self.lesson_contexts.get(session_id, {})

    def update_lesson_context(self, session_id: str, context_updates: Dict) -> None:
        """
        Update lesson context
        """
        if session_id in self.lesson_contexts:
            self.lesson_contexts[session_id].update(context_updates)

    def end_session(self, session_id: str) -> Optional[LessonSession]:
        """
        End session and return final session data
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.updated_at = datetime.now()

            # Could save to database here
            logger.info(f"Ended session {session_id}")

            return session
        return None

    def get_active_sessions(self) -> Dict[str, LessonSession]:
        """
        Get all active sessions
        """
        return self.active_sessions

    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> None:
        """
        Clean up expired sessions
        """
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            age = (current_time - session.updated_at).total_seconds() / 3600
            if age > max_age_hours:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            if session_id in self.lesson_contexts:
                del self.lesson_contexts[session_id]
            logger.info(f"Cleaned up expired session {session_id}")

    def get_session_statistics(self, session_id: str) -> Dict:
        """
        Get session statistics
        """
        if session_id not in self.active_sessions:
            return {}

        session = self.active_sessions[session_id]

        user_messages = [msg for msg in session.messages if msg.role == "user"]
        ai_messages = [msg for msg in session.messages if msg.role == "assistant"]

        return {
            "total_messages": len(session.messages),
            "user_messages": len(user_messages),
            "ai_responses": len(ai_messages),
            "vocabulary_items": len(session.vocabulary_notes),
            "grammar_notes": len(session.grammar_notes),
            "session_duration_minutes": (
                session.updated_at - session.created_at
            ).total_seconds()
            / 60,
            "last_activity": session.updated_at.isoformat(),
        }
