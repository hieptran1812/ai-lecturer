import speech_recognition as sr
import io
import wave
import tempfile
import os
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class STTService:
    def __init__(self):
        """
        Initialize Speech-to-Text service
        """
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)

        logger.info("STT Service initialized")

    def transcribe_audio_file(
        self, audio_data: bytes, language: str = "en-US"
    ) -> Tuple[str, float]:
        """
        Transcribe audio file to text

        Args:
            audio_data: Audio file bytes
            language: Language code for recognition

        Returns:
            Tuple of (transcribed_text, confidence_score)
        """
        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Load audio file
            with sr.AudioFile(temp_file_path) as source:
                audio = self.recognizer.record(source)

            # Clean up temporary file
            os.unlink(temp_file_path)

            # Recognize speech
            try:
                # Try Google Speech Recognition first
                text = self.recognizer.recognize_google(audio, language=language)
                confidence = 0.8  # Google API doesn't return confidence, estimate

            except sr.RequestError:
                # Fallback to offline recognition
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    confidence = 0.6  # Lower confidence for offline
                except sr.RequestError:
                    raise Exception(
                        "Could not request results from speech recognition service"
                    )

            return text, confidence

        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return "", 0.0
        except Exception as e:
            logger.error(f"STT Error: {str(e)}")
            raise Exception(f"Speech recognition failed: {str(e)}")

    def transcribe_microphone(
        self, language: str = "en-US", timeout: int = 5
    ) -> Tuple[str, float]:
        """
        Transcribe audio from microphone

        Args:
            language: Language code for recognition
            timeout: Timeout in seconds

        Returns:
            Tuple of (transcribed_text, confidence_score)
        """
        try:
            with self.microphone as source:
                logger.info("Listening for speech...")
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=10
                )

            # Recognize speech
            try:
                text = self.recognizer.recognize_google(audio, language=language)
                confidence = 0.8

            except sr.RequestError:
                # Fallback to offline recognition
                text = self.recognizer.recognize_sphinx(audio)
                confidence = 0.6

            return text, confidence

        except sr.WaitTimeoutError:
            logger.warning("Listening timeout")
            return "", 0.0
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return "", 0.0
        except Exception as e:
            logger.error(f"STT Error: {str(e)}")
            raise Exception(f"Speech recognition failed: {str(e)}")

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages
        """
        return [
            "en-US",
            "en-GB",
            "en-AU",  # English variants
            "vi-VN",  # Vietnamese
            "zh-CN",
            "zh-TW",  # Chinese variants
            "ja-JP",  # Japanese
            "ko-KR",  # Korean
            "fr-FR",  # French
            "de-DE",  # German
            "es-ES",  # Spanish
        ]


# Initialize global STT service instance
stt_service = None


def get_stt_service() -> STTService:
    """
    Get or create STT service instance (singleton pattern)
    """
    global stt_service
    if stt_service is None:
        stt_service = STTService()
    return stt_service
