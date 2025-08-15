import assemblyai as aai
from typing import Optional, Tuple
from utils.config import Config
from utils.logger import get_logger
from models.schemas import TranscriptionResponse, ErrorType

logger = get_logger("stt_service")


class STTService:
    """Speech-to-Text service using AssemblyAI"""
    
    def __init__(self):
        self.api_key = Config.ASSEMBLYAI_API_KEY
        self._configure_assemblyai()
    
    def _configure_assemblyai(self) -> None:
        """Configure AssemblyAI with API key"""
        if not Config.is_api_key_configured('ASSEMBLYAI_API_KEY'):
            logger.warning("AssemblyAI API key not configured")
            return
        
        aai.settings.api_key = self.api_key
        logger.info("AssemblyAI configured successfully")
    
    def transcribe_audio(self, audio_data: bytes) -> Tuple[bool, TranscriptionResponse, Optional[ErrorType]]:
        """
        Transcribe audio data to text
        
        Args:
            audio_data: Raw audio data bytes
            
        Returns:
            Tuple of (success, response, error_type)
        """
        try:
            if not Config.is_api_key_configured('ASSEMBLYAI_API_KEY'):
                logger.error("AssemblyAI API key not configured")
                return False, TranscriptionResponse(
                    success=False,
                    transcript="[API key not configured]"
                ), ErrorType.API_KEY_MISSING
            
            logger.info("Starting audio transcription")
            
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_data)
            
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"Transcription failed: {transcript.error}")
                return False, TranscriptionResponse(
                    success=False,
                    transcript=f"[Transcription failed: {transcript.error}]"
                ), ErrorType.STT_ERROR
            
            transcribed_text = transcript.text or ""
            
            if not transcribed_text.strip():
                logger.warning("No speech detected in audio")
                transcribed_text = "[No speech detected]"
            
            logger.info(f"Transcription successful: {transcribed_text[:50]}...")
            
            response = TranscriptionResponse(
                success=True,
                transcript=transcribed_text,
                confidence=getattr(transcript, 'confidence', None),
                audio_duration=getattr(transcript, 'audio_duration', None)
            )
            
            return True, response, None
            
        except Exception as e:
            logger.error(f"STT service error: {str(e)}")
            return False, TranscriptionResponse(
                success=False,
                transcript=f"[Transcription error: {str(e)}]"
            ), ErrorType.STT_ERROR
    
    def is_configured(self) -> bool:
        """Check if the STT service is properly configured"""
        return Config.is_api_key_configured('ASSEMBLYAI_API_KEY')


# Global STT service instance
stt_service = STTService()
