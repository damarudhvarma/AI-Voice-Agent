import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the application"""
    
    # API Keys
    ASSEMBLYAI_API_KEY: str = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here')
    MURF_API_KEY: str = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
    
    # Murf TTS Configuration
    MURF_API_URL: str = "https://api.murf.ai/v1/speech/generate"
    MURF_VOICE_ID: str = "en-US-ken"
    MURF_STYLE: str = "Conversational"
    MURF_SAMPLE_RATE: int = 48000
    MURF_FORMAT: str = "MP3"
    MURF_CHANNEL_TYPE: str = "MONO"
    
    # Gemini LLM Configuration
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # File Upload Configuration
    UPLOAD_FOLDER: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    
    # Timeout Configuration
    REQUEST_TIMEOUT: int = 30
    
    # Chat Configuration
    MAX_CHAT_HISTORY: int = 50
    
    @classmethod
    def is_api_key_configured(cls, key_name: str) -> bool:
        """Check if an API key is properly configured"""
        key_value = getattr(cls, key_name, None)
        return key_value and key_value != f'your_{key_name.lower()}_here'
    
    @classmethod
    def get_api_status(cls) -> dict:
        """Get status of all API configurations"""
        return {
            'assemblyai': 'configured' if cls.is_api_key_configured('ASSEMBLYAI_API_KEY') else 'not_configured',
            'gemini': 'configured' if cls.is_api_key_configured('GEMINI_API_KEY') else 'not_configured',
            'murf': 'configured' if cls.is_api_key_configured('MURF_API_KEY') else 'not_configured'
        }
