try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
import os


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4"

    # TTS Configuration
    tts_model_name: str = "microsoft/speecht5_tts"
    tts_vocoder_name: str = "microsoft/speecht5_hifigan"

    # STT Configuration
    stt_model_name: str = "openai/whisper-base"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]

    # Session Configuration
    max_session_duration: int = 3600  # 1 hour

    # File Upload Configuration
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list = [".pdf", ".txt", ".docx", ".md"]

    # Database Configuration (if needed)
    database_url: str = "sqlite:///./ai_teacher.db"

    class Config:
        env_file = ".env"


settings = Settings()
