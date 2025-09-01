import google.generativeai as genai
from typing import Optional, Tuple, List, Generator
from utils.config import Config
from utils.logger import get_logger
from models.schemas import ChatMessage, MessageRole, ErrorType
from services.web_search_service import web_search_service
from services.voice_commands_service import voice_commands_service

logger = get_logger("llm_service")


class LLMService:
    """Language Model service using Google Gemini"""
    
    def __init__(self):
        self.model_name = Config.GEMINI_MODEL
        # Don't configure Gemini at initialization - do it per request
        
        # Enhanced Witty Tech Guru Persona with Web Search and Voice Commands
        self.persona_prompt = """You are a witty, confident, and intelligent tech guru with web search capabilities and smart voice commands! You always explain things clearly and accurately, but with a humorous and engaging twist. You make light jokes, use geeky/tech references, and keep the conversation fun while staying helpful. Your tone should be playful yet professional—like a smart friend who's also a bit sarcastic but always reliable. Never be boring; always aim to make the user smile while learning something.

You have access to:
1. Real-time web search when users ask for current information, facts, or want you to look something up
2. Smart voice commands for calculations, weather, reminders, notes, conversions, and more
3. When a voice command is executed, you'll receive the result and should present it naturally in your witty style

Key traits:
- Humorous, confident, slightly sarcastic but friendly
- Uses geeky/tech references and playful jokes
- Makes analogies to pop culture, coding, and tech concepts
- Speaks like a confident coder who knows the answer but keeps it fun
- Uses occasional meme-like humor
- Always answers clearly & intelligently, but wraps it in humor
- Engages with people like an expert who loves what they do
- Gets excited about finding real-time information through web search
- Celebrates successful voice command executions with enthusiasm

Remember: Be helpful first, funny second. Make sure your technical information is accurate while keeping the conversation engaging and entertaining. When you perform web searches or execute voice commands, be enthusiastic about the functionality you can provide!"""
    
    def _get_current_api_key(self) -> str:
        """Get the current user-provided API key"""
        return Config.get_effective_api_key('GEMINI_API_KEY')
    
    def _configure_gemini(self) -> bool:
        """Configure Gemini with current user-provided API key"""
        if not Config.is_api_key_configured('GEMINI_API_KEY'):
            logger.error("Gemini API key not configured by user")
            return False
        
        current_key = self._get_current_api_key()
        if not current_key:
            logger.error("No user-provided Gemini API key available")
            return False
            
        genai.configure(api_key=current_key)
        logger.info("Gemini configured with user-provided API key")
        return True
        
    
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
            # Configure Gemini with user-provided API key for this request
            if not self._configure_gemini():
                logger.error("Cannot generate response: User must provide Gemini API key")
                return False, "[Please configure Gemini API key in settings]", ErrorType.API_KEY_MISSING
            
            if not prompt.strip():
                logger.error("Empty prompt provided")
                return False, "[Empty prompt provided]", ErrorType.LLM_ERROR
            
            logger.info(f"Generating LLM response for prompt: {prompt[:50]}...")
            
            # Check if this is a voice command first
            command_result = None
            voice_command_text = ""
            
            command_detection = voice_commands_service.detect_command(prompt)
            if command_detection:
                command_type, parameters = command_detection
                logger.info(f"Detected voice command: {command_type}")
                command_result = voice_commands_service.execute_command(command_type, parameters, prompt)
                
                if command_result.success:
                    voice_command_text = f"\n\n[VOICE COMMAND EXECUTED: {command_type.upper()}]\n"
                    voice_command_text += f"Result: {command_result.response}\n"
                    voice_command_text += f"[END OF VOICE COMMAND RESULT]\n\n"
                    logger.info(f"Voice command successful: {command_type}")
                else:
                    voice_command_text = f"\n\n[VOICE COMMAND ERROR: {command_result.response}]\n\n"
                    logger.warning(f"Voice command failed: {command_result.response}")
            
            # Check if this is a web search request (only if not a voice command)
            search_query = None
            search_results_text = ""
            
            if not command_result:  # Only search if no voice command was executed
                search_query = web_search_service.detect_search_intent(prompt)
                
                if search_query and web_search_service.is_configured():
                    logger.info(f"Detected search intent for query: {search_query}")
                    success, search_results, error = web_search_service.search(search_query)
                    
                    if success and search_results:
                        search_results_text = f"\n\n[WEB SEARCH RESULTS FOR '{search_query}']\n"
                        search_results_text += web_search_service.format_search_results(search_results, search_query)
                        search_results_text += "\n[END OF SEARCH RESULTS]\n\n"
                        logger.info(f"Web search successful: {len(search_results)} results found")
                    elif error:
                        search_results_text = f"\n\n[WEB SEARCH ERROR: {error}]\n\n"
                        logger.warning(f"Web search failed: {error}")
            
            # Build context from conversation history
            all_context_data = voice_command_text + search_results_text
            full_prompt = self._build_context_prompt(prompt, conversation_history, all_context_data)
            
            # Configure for creative persona responses
            generation_config = genai.types.GenerationConfig(
                temperature=0.8,  # Slightly higher for more creative/humorous responses
                max_output_tokens=600,  # Allow a bit more room for personality
                top_p=0.8,
                top_k=20
            )
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(full_prompt, generation_config=generation_config)
            
            if not response.text:
                logger.error("No response generated from Gemini")
                return False, "[No response generated]", ErrorType.LLM_ERROR
            
            response_text = response.text.strip()
            logger.info(f"LLM response generated: {response_text[:100]}...")
            
            return True, response_text, None
            
        except Exception as e:
            logger.error(f"LLM service error: {str(e)}")
            return False, f"[LLM error: {str(e)}]", ErrorType.LLM_ERROR
    
    def _build_context_prompt(self, current_prompt: str, conversation_history: Optional[List[ChatMessage]] = None, search_data: str = "") -> str:
        """
        Build a context-aware prompt from conversation history with persona and search data
        
        Args:
            current_prompt: The current user prompt
            conversation_history: List of previous messages
            search_data: Any web search results to include
            
        Returns:
            Formatted prompt with persona, context, and search data
        """
        # Start with persona instructions
        full_prompt = self.persona_prompt + "\n\n"
        
        # Add search data if available
        if search_data:
            full_prompt += search_data
        
        if not conversation_history:
            full_prompt += f"User: {current_prompt}\n\nAssistant:"
            return full_prompt
        
        # Limit history to recent messages to avoid token limits
        recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
        
        context_messages = []
        for msg in recent_history[:-1]:  # Exclude current message
            if msg.role == MessageRole.USER:
                context_messages.append(f"User: {msg.content}")
            else:
                context_messages.append(f"Assistant: {msg.content}")
        
        if context_messages:
            full_prompt += "Previous conversation:\n" + "\n".join(context_messages) + f"\n\nUser: {current_prompt}\n\nAssistant:"
        else:
            full_prompt += f"User: {current_prompt}\n\nAssistant:"
            
        return full_prompt
    
    def generate_streaming_response(self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None) -> Generator[str, None, None]:
        """
        Generate streaming response from LLM
        
        Args:
            prompt: The input prompt
            conversation_history: Optional conversation history for context
            
        Yields:
            Text chunks as they are generated
        """
        try:
            # Configure Gemini with user-provided API key for this request
            if not self._configure_gemini():
                logger.error("Cannot generate streaming response: User must provide Gemini API key")
                yield "[Please configure Gemini API key in settings]"
                return
            
            if not prompt.strip():
                logger.error("Empty prompt provided")
                yield "[Empty prompt provided]"
                return
            
            logger.info(f"Generating streaming LLM response for prompt: {prompt[:50]}...")
            
            # Check if this is a voice command first
            command_result = None
            voice_command_text = ""
            
            command_detection = voice_commands_service.detect_command(prompt)
            if command_detection:
                command_type, parameters = command_detection
                logger.info(f"Detected voice command: {command_type}")
                command_result = voice_commands_service.execute_command(command_type, parameters, prompt)
                
                if command_result.success:
                    voice_command_text = f"\n\n[VOICE COMMAND EXECUTED: {command_type.upper()}]\n"
                    voice_command_text += f"Result: {command_result.response}\n"
                    voice_command_text += f"[END OF VOICE COMMAND RESULT]\n\n"
                    logger.info(f"Voice command successful: {command_type}")
                else:
                    voice_command_text = f"\n\n[VOICE COMMAND ERROR: {command_result.response}]\n\n"
                    logger.warning(f"Voice command failed: {command_result.response}")
            
            # Check if this is a web search request (only if not a voice command)
            search_query = None
            search_results_text = ""
            
            if not command_result:  # Only search if no voice command was executed
                search_query = web_search_service.detect_search_intent(prompt)
                
                if search_query and web_search_service.is_configured():
                    logger.info(f"Detected search intent for query: {search_query}")
                    success, search_results, error = web_search_service.search(search_query)
                    
                    if success and search_results:
                        search_results_text = f"\n\n[WEB SEARCH RESULTS FOR '{search_query}']\n"
                        search_results_text += web_search_service.format_search_results(search_results, search_query)
                        search_results_text += "\n[END OF SEARCH RESULTS]\n\n"
                        logger.info(f"Web search successful: {len(search_results)} results found")
                    elif error:
                        search_results_text = f"\n\n[WEB SEARCH ERROR: {error}]\n\n"
                        logger.warning(f"Web search failed: {error}")
            
            # Build context from conversation history
            all_context_data = voice_command_text + search_results_text
            full_prompt = self._build_context_prompt(prompt, conversation_history, all_context_data)
            
            # Configure for creative persona streaming responses
            generation_config = genai.types.GenerationConfig(
                temperature=0.8,  # Slightly higher for more creative/humorous responses
                max_output_tokens=600,  # Allow a bit more room for personality
                top_p=0.8,
                top_k=20
            )
            
            model = genai.GenerativeModel(self.model_name)
            response_stream = model.generate_content(full_prompt, generation_config=generation_config, stream=True)
            
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            
            logger.info("Streaming LLM response completed")
            
        except Exception as e:
            logger.error(f"LLM streaming service error: {str(e)}")
            yield f"[LLM streaming error: {str(e)}]"
    
    def is_configured(self) -> bool:
        """Check if the LLM service is properly configured"""
        return Config.is_api_key_configured('GEMINI_API_KEY')


# Global LLM service instance
llm_service = LLMService()
