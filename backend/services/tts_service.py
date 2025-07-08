import torch
import torchaudio
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import numpy as np
import io
import base64
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, model_name: str = "microsoft/speecht5_tts"):
        """
        Initialize TTS service with bilingual support (English and Vietnamese)
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = SpeechT5Processor.from_pretrained(model_name)
        self.model = SpeechT5ForTextToSpeech.from_pretrained(model_name).to(self.device)
        self.vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").to(
            self.device
        )

        # Load speaker embeddings
        embeddings_dataset = load_dataset(
            "Matthijs/cmu-arctic-xvectors", split="validation"
        )
        self.speaker_embeddings = (
            torch.tensor(embeddings_dataset[7306]["xvector"])
            .unsqueeze(0)
            .to(self.device)
        )

        logger.info(f"TTS Service initialized on {self.device}")

    def text_to_speech(self, text: str, language: str = "en") -> bytes:
        """
        Convert text to speech

        Args:
            text: Input text to synthesize
            language: Language code ("en" for English, "vi" for Vietnamese)

        Returns:
            Audio bytes in WAV format
        """
        try:
            # Preprocess text based on language
            if language == "vi":
                # Add Vietnamese-specific preprocessing if needed
                text = self._preprocess_vietnamese_text(text)

            # Tokenize and process
            inputs = self.processor(text=text, return_tensors="pt").to(self.device)

            # Generate speech
            with torch.no_grad():
                speech = self.model.generate_speech(
                    inputs["input_ids"], self.speaker_embeddings, vocoder=self.vocoder
                )

            # Convert to audio bytes
            speech_np = speech.cpu().numpy()

            # Convert to WAV format
            buffer = io.BytesIO()
            torchaudio.save(
                buffer, torch.from_numpy(speech_np).unsqueeze(0), 16000, format="wav"
            )
            buffer.seek(0)

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"TTS Error: {str(e)}")
            raise Exception(f"Text-to-speech failed: {str(e)}")

    def _preprocess_vietnamese_text(self, text: str) -> str:
        """
        Preprocess Vietnamese text for better TTS quality
        """
        # Add Vietnamese-specific text normalization here
        # For now, just return the text as-is
        return text

    def text_to_speech_base64(self, text: str, language: str = "en") -> str:
        """
        Convert text to speech and return as base64 encoded string
        """
        audio_bytes = self.text_to_speech(text, language)
        return base64.b64encode(audio_bytes).decode("utf-8")

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages
        """
        return ["en", "vi"]


# Initialize global TTS service instance
tts_service = None


def get_tts_service() -> TTSService:
    """
    Get or create TTS service instance (singleton pattern)
    """
    global tts_service
    if tts_service is None:
        tts_service = TTSService()
    return tts_service
