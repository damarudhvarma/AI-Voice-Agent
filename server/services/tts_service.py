import requests
from typing import Optional, Tuple
from utils.config import Config
from utils.logger import get_logger
from models.schemas import TTSResponse, ErrorType

logger = get_logger("tts_service")


class TTSService:
    """Text-to-Speech service using Murf API"""
    
    def __init__(self):
        self.api_key = Config.MURF_API_KEY
        self.api_url = Config.MURF_API_URL
        self.voice_id = Config.MURF_VOICE_ID
        self.style = Config.MURF_STYLE
        self.sample_rate = Config.MURF_SAMPLE_RATE
        self.format = Config.MURF_FORMAT
        self.channel_type = Config.MURF_CHANNEL_TYPE
    
    def generate_speech(self, text: str, voice_id: Optional[str] = None) -> Tuple[bool, TTSResponse, Optional[ErrorType]]:
        """
        Generate speech from text using Murf API
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID to override default
            
        Returns:
            Tuple of (success, response, error_type)
        """
        try:
            if not Config.is_api_key_configured('MURF_API_KEY'):
                logger.error("Murf API key not configured")
                return False, self._create_fallback_response(ErrorType.API_KEY_MISSING), ErrorType.API_KEY_MISSING
            
            if not text.strip():
                logger.error("Empty text provided for TTS")
                return False, TTSResponse(
                    success=False,
                    text=text,
                    fallback_text="[Empty text provided]"
                ), ErrorType.TTS_ERROR
            
            logger.info(f"Generating speech for text: {text[:50]}...")
            
            # Prepare the payload
            payload = {
                "voiceId": voice_id or self.voice_id,
                "style": self.style,
                "text": text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": self.sample_rate,
                "format": self.format,
                "channelType": self.channel_type,
                "pronunciationDictionary": {},
                "encodeAsBase64": False,
                "variation": 1,
                "audioDuration": 0
            }
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': self.api_key
            }
            
            # Make request to Murf API
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                murf_response = response.json()
                audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
                
                if audio_url:
                    logger.info("TTS generation successful")
                    return True, TTSResponse(
                        success=True,
                        audio_url=audio_url,
                        text=text,
                        is_fallback=False
                    ), None
                else:
                    logger.warning("Murf API returned no audio URL")
                    return False, self._create_fallback_response(ErrorType.TTS_ERROR), ErrorType.TTS_ERROR
            else:
                logger.error(f"Murf API error: {response.status_code}")
                return False, self._create_fallback_response(ErrorType.TTS_ERROR), ErrorType.TTS_ERROR
                
        except requests.exceptions.Timeout:
            logger.error("Murf API request timed out")
            return False, self._create_fallback_response(ErrorType.TIMEOUT_ERROR), ErrorType.TIMEOUT_ERROR
        except requests.exceptions.RequestException as e:
            logger.error(f"Murf API network error: {str(e)}")
            return False, self._create_fallback_response(ErrorType.TTS_ERROR), ErrorType.TTS_ERROR
        except Exception as e:
            logger.error(f"TTS service unexpected error: {str(e)}")
            return False, self._create_fallback_response(ErrorType.TTS_ERROR), ErrorType.TTS_ERROR
    
    def _create_fallback_response(self, error_type: ErrorType) -> TTSResponse:
        """Create a fallback response when TTS fails"""
        fallback_texts = {
            ErrorType.STT_ERROR: "I'm having trouble hearing you right now. Could you please try speaking again?",
            ErrorType.LLM_ERROR: "I'm having trouble thinking right now. My AI brain seems to be taking a coffee break. Please try again in a moment.",
            ErrorType.TTS_ERROR: "I'm having trouble speaking right now, but I'm still listening and thinking!",
            ErrorType.GENERAL_ERROR: "I'm experiencing some technical difficulties right now. Please bear with me while I get back on track.",
            ErrorType.API_KEY_MISSING: "I'm not properly configured right now. Please check my settings and try again.",
            ErrorType.TIMEOUT_ERROR: "I'm taking a bit longer than usual to respond. Please try again in a moment."
        }
        
        return TTSResponse(
            success=True,
            audio_url=None,
            fallback_text=fallback_texts.get(error_type, fallback_texts[ErrorType.GENERAL_ERROR]),
            error_type=error_type,
            is_fallback=True
        )
    
    def is_configured(self) -> bool:
        """Check if the TTS service is properly configured"""
        return Config.is_api_key_configured('MURF_API_KEY')


# Global TTS service instance
tts_service = TTSService()
