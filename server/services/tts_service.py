import requests
from typing import Optional, Tuple
from utils.config import Config
from utils.logger import get_logger
from models.schemas import TTSResponse, ErrorType

logger = get_logger("tts_service")


class TTSService:
    """Text-to-Speech service using Murf API"""
    
    def __init__(self):
        # Configuration constants (not API key)
        self.api_url = Config.MURF_API_URL
        self.voice_id = Config.MURF_VOICE_ID
        self.style = Config.MURF_STYLE
        self.sample_rate = Config.MURF_SAMPLE_RATE
        self.format = Config.MURF_FORMAT
        self.channel_type = Config.MURF_CHANNEL_TYPE
    
    def _get_current_api_key(self) -> str:
        """Get the current user-provided API key"""
        return Config.get_effective_api_key('MURF_API_KEY')
    
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
                logger.error("Murf API key not configured by user")
                return False, self._create_fallback_response(ErrorType.API_KEY_MISSING), ErrorType.API_KEY_MISSING
            
            # Get current user-provided API key
            current_api_key = self._get_current_api_key()
            if not current_api_key:
                logger.error("No user-provided Murf API key available")
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
                'api-key': current_api_key
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
    
    def generate_base64_audio(self, text: str) -> Tuple[bool, str, Optional[ErrorType]]:
        """
        Generate base64 encoded audio from text using Murf API
        
        Args:
            text: Text to convert to base64 audio
            
        Returns:
            Tuple of (success, base64_audio, error_type)
        """
        try:
            if not Config.is_api_key_configured('MURF_API_KEY'):
                logger.error("Murf API key not configured")
                return False, "", ErrorType.API_KEY_MISSING
            
            if not text.strip():
                logger.error("Empty text provided for base64 audio")
                return False, "", ErrorType.TTS_ERROR
            
            logger.info(f"Generating base64 audio for text: {text[:50]}...")
            logger.info(f"Using voice_id: {self.voice_id}")
            logger.info(f"Using API URL: {self.api_url}")
            
            # First, generate regular audio file
            payload = {
                "voiceId": self.voice_id,
                "style": self.style,
                "text": text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": self.sample_rate,
                "format": self.format,
                "channelType": self.channel_type,
                "pronunciationDictionary": {},
                "variation": 1,
                "audioDuration": 0
            }
            
            logger.info(f"Murf API payload: {payload}")
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': current_api_key
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
                    # Download the audio file and convert to base64
                    logger.info(f"Downloading audio from: {audio_url}")
                    audio_response = requests.get(audio_url, timeout=Config.REQUEST_TIMEOUT)
                    
                    if audio_response.status_code == 200:
                        import base64
                        audio_data = audio_response.content
                        base64_audio = base64.b64encode(audio_data).decode('utf-8')
                        logger.info("Base64 audio generation successful")
                        return True, base64_audio, None
                    else:
                        logger.error(f"Failed to download audio file: {audio_response.status_code}")
                        return False, "", ErrorType.TTS_ERROR
                else:
                    logger.warning(f"Murf API returned no audio URL. Full response: {murf_response}")
                    return False, "", ErrorType.TTS_ERROR
            else:
                logger.error(f"Murf API error: {response.status_code} - {response.text}")
                return False, "", ErrorType.TTS_ERROR
                
        except requests.exceptions.Timeout:
            logger.error("Murf API request timed out")
            return False, "", ErrorType.TIMEOUT_ERROR
        except requests.exceptions.RequestException as e:
            logger.error(f"Murf API network error: {str(e)}")
            return False, "", ErrorType.TTS_ERROR
        except Exception as e:
            logger.error(f"Base64 audio generation error: {str(e)}")
            return False, "", ErrorType.TTS_ERROR
    
    def generate_fast_base64_audio(self, text: str) -> Tuple[bool, str, Optional[ErrorType]]:
        """
        Generate base64 audio quickly with minimal chunk size for faster streaming
        
        Args:
            text: Text to convert to base64 audio
            
        Returns:
            Tuple of (success, base64_audio, error_type)
        """
        try:
            if not Config.is_api_key_configured('MURF_API_KEY'):
                logger.error("Murf API key not configured")
                return False, "", ErrorType.API_KEY_MISSING
            
            if not text.strip():
                logger.error("Empty text provided for fast audio")
                return False, "", ErrorType.TTS_ERROR
            
            logger.info(f"🚀 Fast audio generation for: {text[:30]}...")
            
            # Optimized payload for faster generation
            payload = {
                "voiceId": self.voice_id,
                "style": self.style,
                "text": text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": 24000,  # Reduced sample rate for faster processing
                "format": "MP3",
                "channelType": "MONO",
                "pronunciationDictionary": {},
                "variation": 1,
                "audioDuration": 0
            }
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': current_api_key
            }
            
            # Make request with reduced timeout for faster response
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=15  # Reduced timeout for faster response
            )
            
            if response.status_code == 200:
                murf_response = response.json()
                audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
                
                if audio_url:
                    # Download and convert to base64
                    audio_response = requests.get(audio_url, timeout=10)
                    
                    if audio_response.status_code == 200:
                        import base64
                        audio_data = audio_response.content
                        base64_audio = base64.b64encode(audio_data).decode('utf-8')
                        logger.info("🚀 Fast audio generation successful")
                        return True, base64_audio, None
                    else:
                        logger.error(f"Failed to download audio file: {audio_response.status_code}")
                        return False, "", ErrorType.TTS_ERROR
                else:
                    logger.warning(f"Murf API returned no audio URL")
                    return False, "", ErrorType.TTS_ERROR
            else:
                logger.error(f"Murf API error: {response.status_code}")
                return False, "", ErrorType.TTS_ERROR
                
        except requests.exceptions.Timeout:
            logger.error("Fast audio generation timed out")
            return False, "", ErrorType.TIMEOUT_ERROR
        except Exception as e:
            logger.error(f"Fast audio generation error: {str(e)}")
            return False, "", ErrorType.TTS_ERROR

    def generate_streaming_base64_audio(self, text: str, chunk_size: int = 512) -> Tuple[bool, list, Optional[ErrorType]]:
        """
        Generate base64 encoded audio from text using Murf API and return as chunks
        
        Args:
            text: Text to convert to base64 audio
            chunk_size: Size of each base64 chunk in characters
            
        Returns:
            Tuple of (success, base64_chunks_list, error_type)
        """
        try:
            if not Config.is_api_key_configured('MURF_API_KEY'):
                logger.error("Murf API key not configured")
                return False, [], ErrorType.API_KEY_MISSING
            
            if not text.strip():
                logger.error("Empty text provided for base64 audio")
                return False, [], ErrorType.TTS_ERROR
            
            logger.info(f"Generating streaming base64 audio for text: {text[:50]}...")
            logger.info(f"Using voice_id: {self.voice_id}")
            logger.info(f"Using API URL: {self.api_url}")
            
            # First, generate regular audio file
            payload = {
                "voiceId": self.voice_id,
                "style": self.style,
                "text": text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": self.sample_rate,
                "format": self.format,
                "channelType": self.channel_type,
                "pronunciationDictionary": {},
                "variation": 1,
                "audioDuration": 0
            }
            
            logger.info(f"Murf API payload: {payload}")
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': current_api_key
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
                    # Download the audio file and convert to base64
                    logger.info(f"Downloading audio from: {audio_url}")
                    audio_response = requests.get(audio_url, timeout=Config.REQUEST_TIMEOUT)
                    
                    if audio_response.status_code == 200:
                        import base64
                        audio_data = audio_response.content
                        base64_audio = base64.b64encode(audio_data).decode('utf-8')
                        
                        # Split base64 audio into chunks
                        base64_chunks = []
                        for i in range(0, len(base64_audio), chunk_size):
                            chunk = base64_audio[i:i + chunk_size]
                            base64_chunks.append(chunk)
                        
                        logger.info(f"Base64 audio streaming successful - {len(base64_chunks)} chunks")
                        logger.info(f"Total base64 length: {len(base64_audio)} characters")
                        logger.info(f"Chunk size: {chunk_size} characters")
                        
                        return True, base64_chunks, None
                    else:
                        logger.error(f"Failed to download audio file: {audio_response.status_code}")
                        return False, [], ErrorType.TTS_ERROR
                else:
                    logger.warning(f"Murf API returned no audio URL. Full response: {murf_response}")
                    return False, [], ErrorType.TTS_ERROR
            else:
                logger.error(f"Murf API error: {response.status_code} - {response.text}")
                return False, [], ErrorType.TTS_ERROR
                
        except requests.exceptions.Timeout:
            logger.error("Murf API request timed out")
            return False, [], ErrorType.TIMEOUT_ERROR
        except requests.exceptions.RequestException as e:
            logger.error(f"Murf API network error: {str(e)}")
            return False, [], ErrorType.TTS_ERROR
        except Exception as e:
            logger.error(f"Base64 audio streaming error: {str(e)}")
            return False, [], ErrorType.TTS_ERROR

    def is_configured(self) -> bool:
        """Check if the TTS service is properly configured"""
        return Config.is_api_key_configured('MURF_API_KEY')


# Global TTS service instance
tts_service = TTSService()
