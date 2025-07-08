# Backend initialization
from .config import settings
from .agents.ai_teacher import get_ai_teacher
from .services.tts_service import get_tts_service
from .services.stt_service import get_stt_service

__version__ = "1.0.0"


def initialize_services():
    """
    Initialize all backend services
    """
    try:
        # Initialize AI Teacher
        ai_teacher = get_ai_teacher()
        print("✅ AI Teacher initialized")

        # Initialize TTS Service
        tts_service = get_tts_service()
        print("✅ TTS Service initialized")

        # Initialize STT Service
        stt_service = get_stt_service()
        print("✅ STT Service initialized")

        print(f"🎓 AI Teacher Backend v{__version__} ready!")
        return True

    except Exception as e:
        print(f"❌ Failed to initialize services: {str(e)}")
        return False
