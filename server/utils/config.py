import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# Try to load from server directory first, then root directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
load_dotenv()  # Also try root directory


class Config:
    """Configuration class for the application"""
    
    # Environment API Keys (fallback)
    ASSEMBLYAI_API_KEY: str = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here')
    MURF_API_KEY: str = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
    SERP_API_KEY: str = os.getenv('SERP_API_KEY', 'your_serp_api_key_here')
    OPENWEATHER_API_KEY: str = os.getenv('OPENWEATHER_API_KEY', 'your_openweather_api_key_here')
    EXCHANGE_RATE_API_KEY: str = os.getenv('EXCHANGE_RATE_API_KEY', 'your_exchange_rate_api_key_here')
    NEWS_API_KEY: str = os.getenv('NEWS_API_KEY', 'your_newsapi_key_here')
    
    # User-provided API Keys (priority over environment)
    _user_api_keys = {}
    
    @classmethod
    def set_user_api_key(cls, key_name: str, key_value: str) -> None:
        """Set a user-provided API key"""
        cls._user_api_keys[key_name] = key_value
    
    @classmethod
    def get_user_api_key(cls, key_name: str) -> str:
        """Get a user-provided API key"""
        return cls._user_api_keys.get(key_name, '')
    
    @classmethod
    def clear_user_api_keys(cls) -> None:
        """Clear all user-provided API keys"""
        cls._user_api_keys.clear()
    
    @classmethod
    def get_effective_api_key(cls, key_name: str) -> str:
        """Get the effective API key (ONLY user-provided, no environment fallback)"""
        # Only return user-provided keys, no environment fallback for mandatory services
        user_key = cls._user_api_keys.get(key_name, '')
        if user_key and len(user_key.strip()) > 10:
            return user_key.strip()
        
        # For mandatory keys (AssemblyAI, Gemini, Murf), return empty if not user-provided
        mandatory_keys = {'ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY'}
        if key_name in mandatory_keys:
            return ''
        
        # Optional keys can still fallback to environment
        env_key = getattr(cls, key_name, '')
        return env_key
    
    @classmethod
    def get_all_user_api_keys(cls) -> dict:
        """Get all user-provided API keys (for UI display)"""
        return cls._user_api_keys.copy()
    
    @classmethod
    def set_multiple_user_api_keys(cls, api_keys: dict) -> None:
        """Set multiple user-provided API keys at once"""
        for key_name, key_value in api_keys.items():
            if key_value and key_value.strip():
                cls._user_api_keys[key_name] = key_value.strip()
    
    @classmethod
    def get_api_key_sources(cls) -> dict:
        """Get info about API key sources (user vs environment)"""
        sources = {}
        key_names = ['ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY', 'SERP_API_KEY', 
                     'OPENWEATHER_API_KEY', 'EXCHANGE_RATE_API_KEY', 'NEWS_API_KEY']
        
        for key_name in key_names:
            user_key = cls._user_api_keys.get(key_name, '')
            env_key = getattr(cls, key_name, '')
            
            if user_key and len(user_key.strip()) > 10:
                sources[key_name] = {'source': 'user', 'configured': True}
            elif env_key and len(env_key) > 10 and not env_key.startswith('your_'):
                sources[key_name] = {'source': 'environment', 'configured': True}
            else:
                sources[key_name] = {'source': 'none', 'configured': False}
        
        return sources
    
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
    
    @classmethod
    def ensure_upload_folder(cls):
        """Ensure upload folder exists"""
        if not os.path.exists(cls.UPLOAD_FOLDER):
            os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
    
    # Timeout Configuration
    REQUEST_TIMEOUT: int = 30
    
    # Chat Configuration
    MAX_CHAT_HISTORY: int = 50
    
    @classmethod
    def is_api_key_configured(cls, key_name: str) -> bool:
        """Check if an API key is properly configured (user-provided only for mandatory keys)"""
        mandatory_keys = {'ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY'}
        
        if key_name in mandatory_keys:
            # For mandatory keys, ONLY check user-provided keys
            user_key = cls._user_api_keys.get(key_name, '')
            return user_key and len(user_key.strip()) > 10
        else:
            # For optional keys, check effective key (user or environment)
            key_value = cls.get_effective_api_key(key_name)
            default_values = [
                f'your_{key_name.lower()}_here',
                'your_newsapi_key_here',
                'your_news_api_key_here'
            ]
            return key_value and key_value not in default_values and len(key_value) > 10
    
    @classmethod
    def get_api_status(cls) -> dict:
        """Get status of all API configurations"""
        return {
            'assemblyai': 'configured' if cls.is_api_key_configured('ASSEMBLYAI_API_KEY') else 'not_configured',
            'gemini': 'configured' if cls.is_api_key_configured('GEMINI_API_KEY') else 'not_configured',
            'murf': 'configured' if cls.is_api_key_configured('MURF_API_KEY') else 'not_configured',
            'serp_api': 'configured' if cls.is_api_key_configured('SERP_API_KEY') else 'not_configured',
            'openweather': 'configured' if cls.is_api_key_configured('OPENWEATHER_API_KEY') else 'not_configured',
            'exchange_rate': 'configured' if cls.is_api_key_configured('EXCHANGE_RATE_API_KEY') else 'not_configured',
            'news_api': 'configured' if cls.is_api_key_configured('NEWS_API_KEY') else 'not_configured'
        }
