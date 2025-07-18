from typing import List, Dict, Any, Optional
import openai
import json
import logging
from datetime import datetime
from ..models.schemas import (
    ChatMessage,
    SessionSummary,
    StudentProfile,
    LessonSession,
)
from ..config import settings

logger = logging.getLogger(__name__)


class AITeacherAgent:
    def __init__(self):
        """
        Initialize AI Teacher Agent with OpenAI integration
        """
        # Check if API key is provided
        if not settings.openai_api_key:
            logger.warning(
                "OpenAI API key not provided. Using mock responses for testing."
            )
            self.client = None
            self.model = settings.openai_model
        else:
            try:
                self.client = openai.OpenAI(api_key=settings.openai_api_key)
                self.model = settings.openai_model
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                logger.warning("Falling back to mock responses")
                self.client = None
                self.model = settings.openai_model

        # System prompt for the AI teacher
        self.system_prompt = """
        You are an experienced English teacher AI with expertise in language instruction.
        Your role is to:
        1. Teach English based on provided curriculum and documents
        2. Adapt your teaching style to individual student needs
        3. Provide real-time feedback and encouragement
        4. Extract key vocabulary and grammar points during lessons
        5. Create engaging, interactive learning experiences
        6. Maintain a supportive and patient demeanor
        
        Always respond in a clear, encouraging manner and adjust complexity based on the student's level.
        When teaching, focus on practical usage and real-world examples.
        """

        logger.info("AI Teacher Agent initialized")

    async def process_document(
        self, document_content: str, document_type: str
    ) -> Dict[str, Any]:
        """
        Process uploaded document and create lesson plan

        Args:
            document_content: The content of the uploaded document
            document_type: Type of document (pdf, txt, etc.)

        Returns:
            Dictionary containing lesson structure and key points
        """
        try:
            prompt = f"""
            Analyze this English learning document and create a structured lesson plan:
            
            Document Content:
            {document_content}
            
            Please provide:
            1. Main topics and learning objectives
            2. Key vocabulary words with definitions and examples
            3. Grammar points to focus on
            4. Suggested teaching sequence
            5. Interactive activities or questions
            6. Assessment criteria
            
            Format the response as a JSON object with clear structure.
            """

            response = await self._call_openai(prompt)

            # Parse the response to extract structured data
            lesson_plan = self._parse_lesson_plan(response)

            return lesson_plan

        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")

    async def generate_response(
        self,
        user_message: str,
        lesson_context: Dict[str, Any],
        student_profile: StudentProfile,
        conversation_history: List[ChatMessage],
    ) -> Dict[str, Any]:
        """
        Generate AI teacher response to student input

        Args:
            user_message: Student's message
            lesson_context: Current lesson context and materials
            student_profile: Student's profile and learning preferences
            conversation_history: Previous conversation messages

        Returns:
            Dictionary containing response and extracted learning notes
        """
        try:
            # Build context prompt
            context_prompt = self._build_context_prompt(
                lesson_context, student_profile, conversation_history
            )

            prompt = f"""
            {context_prompt}
            
            Student says: "{user_message}"
            
            Respond as an AI English teacher. Include:
            1. A natural, encouraging response
            2. Any new vocabulary to highlight
            3. Grammar corrections or explanations if needed
            4. Follow-up questions to keep engagement
            
            Also identify:
            - New vocabulary words used (with definitions)
            - Grammar points demonstrated
            - Student's comprehension level
            """

            response = await self._call_openai(prompt)

            # Extract learning components from response
            parsed_response = self._parse_teacher_response(response)

            return parsed_response

        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")

    async def generate_session_summary(
        self, session: LessonSession, student_profile: StudentProfile
    ) -> SessionSummary:
        """
        Generate comprehensive session summary and feedback

        Args:
            session: The completed lesson session
            student_profile: Student's profile

        Returns:
            SessionSummary object with comprehensive feedback
        """
        try:
            # Prepare conversation for analysis
            conversation_text = "\n".join(
                [f"{msg.role}: {msg.content}" for msg in session.messages]
            )

            prompt = f"""
            Analyze this English lesson session and provide comprehensive feedback:
            
            Student Level: {student_profile.level}
            Student Name: {student_profile.name}
            
            Conversation:
            {conversation_text}
            
            Vocabulary Notes: {json.dumps(session.vocabulary_notes, indent=2)}
            Grammar Notes: {json.dumps(session.grammar_notes, indent=2)}
            
            Please provide:
            1. Key concepts covered in the lesson
            2. Student's performance analysis
            3. Areas of strength
            4. Areas for improvement
            5. Specific recommendations for next steps
            6. Vocabulary mastery assessment
            7. Grammar understanding evaluation
            
            Format as a detailed but encouraging summary.
            """

            response = await self._call_openai(prompt)
            summary_data = self._parse_session_summary(response, session.session_id)

            return summary_data

        except Exception as e:
            logger.error(f"Session summary error: {str(e)}")
            raise Exception(f"Failed to generate session summary: {str(e)}")

    async def _call_openai(self, prompt: str) -> str:
        """
        Make API call to OpenAI
        """
        try:
            if not self.client:
                # Return a mock response if OpenAI client is not available
                return """
                {
                    "objectives": ["Basic English conversation skills"],
                    "vocabulary": ["hello", "world", "learn"],
                    "grammar": ["Present tense verbs"],
                    "activities": ["Reading comprehension", "Vocabulary practice"],
                    "raw_content": "Mock lesson plan - OpenAI API not configured"
                }
                """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise Exception(f"AI service error: {str(e)}")

    def _build_context_prompt(
        self,
        lesson_context: Dict[str, Any],
        student_profile: StudentProfile,
        conversation_history: List[ChatMessage],
    ) -> str:
        """
        Build context prompt for AI teacher
        """
        context = f"""
        LESSON CONTEXT:
        Topic: {lesson_context.get('topic', 'General English')}
        Objectives: {lesson_context.get('objectives', [])}
        Key Vocabulary: {lesson_context.get('vocabulary', [])}
        Grammar Focus: {lesson_context.get('grammar', [])}
        
        STUDENT PROFILE:
        Name: {student_profile.name}
        Level: {student_profile.level}
        Preferences: {student_profile.learning_preferences}
        
        RECENT CONVERSATION:
        """

        # Add last few messages for context
        recent_messages = (
            conversation_history[-5:]
            if len(conversation_history) > 5
            else conversation_history
        )
        for msg in recent_messages:
            context += f"{msg.role}: {msg.content}\n"

        return context

    def _parse_lesson_plan(self, response: str) -> Dict[str, Any]:
        """
        Parse AI response into structured lesson plan
        """
        try:
            # Try to parse as JSON first
            if response.strip().startswith("{"):
                return json.loads(response)
            else:
                # Fallback: extract structured information
                return {
                    "objectives": [],
                    "vocabulary": [],
                    "grammar": [],
                    "activities": [],
                    "raw_content": response,
                }
        except json.JSONDecodeError:
            logger.warning("Failed to parse lesson plan as JSON")
            return {"raw_content": response}

    def _parse_teacher_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI teacher response and extract learning components
        """
        return {
            "message": response,
            "vocabulary_items": [],  # Would extract from response
            "grammar_notes": [],  # Would extract from response
            "comprehension_level": "intermediate",  # Would assess from response
            "timestamp": datetime.now(),
        }

    def _parse_session_summary(self, response: str, session_id: str) -> SessionSummary:
        """
        Parse session summary response
        """
        return SessionSummary(
            session_id=session_id,
            key_concepts=[],
            vocabulary_learned=[],
            grammar_covered=[],
            student_performance={},
            recommendations=[],
            next_steps=[],
        )


# Initialize global AI teacher instance
ai_teacher = None


def get_ai_teacher() -> AITeacherAgent:
    """
    Get or create AI teacher instance (singleton pattern)
    """
    global ai_teacher
    if ai_teacher is None:
        ai_teacher = AITeacherAgent()
    return ai_teacher
