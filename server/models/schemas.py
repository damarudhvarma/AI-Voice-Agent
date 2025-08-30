from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ErrorType(str, Enum):
    """Enum for different error types"""
    STT_ERROR = "stt_error"
    LLM_ERROR = "llm_error"
    TTS_ERROR = "tts_error"
    GENERAL_ERROR = "general_error"
    API_KEY_MISSING = "api_key_missing"
    TIMEOUT_ERROR = "timeout_error"


class MessageRole(str, Enum):
    """Enum for message roles in chat"""
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Schema for a single chat message"""
    role: MessageRole
    content: str


class TTSRequest(BaseModel):
    """Schema for TTS request"""
    text: str = Field(..., min_length=1, description="Text to convert to speech")


class TTSResponse(BaseModel):
    """Schema for TTS response"""
    success: bool
    audio_url: Optional[str] = None
    text: Optional[str] = None
    fallback_text: Optional[str] = None
    is_fallback: bool = False
    error_type: Optional[ErrorType] = None


class TranscriptionResponse(BaseModel):
    """Schema for transcription response"""
    success: bool
    transcript: str
    confidence: Optional[float] = None
    audio_duration: Optional[float] = None


class LLMQueryResponse(BaseModel):
    """Schema for LLM query response"""
    success: bool
    transcription: str
    llm_response: str
    audio_url: Optional[str] = None
    voice_id: str = "en-US-ken"
    model: str = "gemini-1.5-flash"


class AgentChatResponse(BaseModel):
    """Schema for agent chat response"""
    success: bool
    session_id: str
    user_message: str
    assistant_response: str
    audio_url: Optional[str] = None
    fallback_text: Optional[str] = None
    message_count: int
    voice_id: str = "en-US-ken"
    model: str = "gemini-1.5-flash"
    is_fallback: bool = False
    error_type: Optional[ErrorType] = None


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response"""
    session_id: str
    messages: List[ChatMessage]
    message_count: int


class HealthCheckResponse(BaseModel):
    """Schema for health check response"""
    status: str
    message: str
    apis: Dict[str, str]
    error_handling: str


class FileInfo(BaseModel):
    """Schema for file upload response"""
    name: str
    content_type: str
    size: int


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    fallback_audio: Optional[Dict[str, Any]] = None
