import google.generativeai as genai
from typing import Optional, Tuple, List
from utils.config import Config
from utils.logger import get_logger
from models.schemas import ChatMessage, MessageRole, ErrorType

logger = get_logger("llm_service")


class LLMService:
    """Language Model service using Google Gemini"""
    
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self._configure_gemini()
    
    def _configure_gemini(self) -> None:
        """Configure Gemini with API key"""
        if not Config.is_api_key_configured('GEMINI_API_KEY'):
            logger.warning("Gemini API key not configured")
            return
        
        genai.configure(api_key=self.api_key)
        logger.info("Gemini configured successfully")
    
    def generate_response(self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None) -> Tuple[bool, str, Optional[ErrorType]]:
        """
        Generate response from LLM
        
        Args:
            prompt: The input prompt
            conversation_history: Optional conversation history for context
            
        Returns:
            Tuple of (success, response_text, error_type)
        """
        try:
            if not Config.is_api_key_configured('GEMINI_API_KEY'):
                logger.error("Gemini API key not configured")
                return False, "[LLM not configured]", ErrorType.API_KEY_MISSING
            
            if not prompt.strip():
                logger.error("Empty prompt provided")
                return False, "[Empty prompt provided]", ErrorType.LLM_ERROR
            
            logger.info(f"Generating LLM response for prompt: {prompt[:50]}...")
            
            # Build context from conversation history
            full_prompt = self._build_context_prompt(prompt, conversation_history)
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(full_prompt)
            
            if not response.text:
                logger.error("No response generated from Gemini")
                return False, "[No response generated]", ErrorType.LLM_ERROR
            
            response_text = response.text.strip()
            logger.info(f"LLM response generated: {response_text[:100]}...")
            
            return True, response_text, None
            
        except Exception as e:
            logger.error(f"LLM service error: {str(e)}")
            return False, f"[LLM error: {str(e)}]", ErrorType.LLM_ERROR
    
    def _build_context_prompt(self, current_prompt: str, conversation_history: Optional[List[ChatMessage]] = None) -> str:
        """
        Build a context-aware prompt from conversation history
        
        Args:
            current_prompt: The current user prompt
            conversation_history: List of previous messages
            
        Returns:
            Formatted prompt with context
        """
        if not conversation_history:
            return current_prompt
        
        # Limit history to recent messages to avoid token limits
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        
        context_messages = []
        for msg in recent_history[:-1]:  # Exclude current message
            if msg.role == MessageRole.USER:
                context_messages.append(f"User: {msg.content}")
            else:
                context_messages.append(f"Assistant: {msg.content}")
        
        if context_messages:
            return "Previous conversation:\n" + "\n".join(context_messages) + f"\n\nUser: {current_prompt}\n\nAssistant:"
        else:
            return current_prompt
    
    def is_configured(self) -> bool:
        """Check if the LLM service is properly configured"""
        return Config.is_api_key_configured('GEMINI_API_KEY')


# Global LLM service instance
llm_service = LLMService()
