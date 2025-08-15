from typing import List, Optional, Dict
from utils.logger import get_logger
from utils.config import Config
from models.schemas import ChatMessage, MessageRole, ChatHistoryResponse

logger = get_logger("chat_manager")


class ChatManager:
    """Manages chat history and sessions"""
    
    def __init__(self):
        # In-memory chat history datastore
        # Key: session_id, Value: list of ChatMessage objects
        self.chat_history_store: Dict[str, List[ChatMessage]] = {}
    
    def add_message(self, session_id: str, role: MessageRole, content: str) -> None:
        """
        Add a message to the chat history for a session
        
        Args:
            session_id: Unique session identifier
            role: Role of the message sender (user/assistant)
            content: Message content
        """
        if session_id not in self.chat_history_store:
            self.chat_history_store[session_id] = []
        
        message = ChatMessage(role=role, content=content)
        self.chat_history_store[session_id].append(message)
        
        # Limit history size to prevent memory issues
        if len(self.chat_history_store[session_id]) > Config.MAX_CHAT_HISTORY:
            self.chat_history_store[session_id] = self.chat_history_store[session_id][-Config.MAX_CHAT_HISTORY:]
        
        logger.info(f"Added {role.value} message to session {session_id}. Total messages: {len(self.chat_history_store[session_id])}")
    
    def get_chat_history(self, session_id: str) -> ChatHistoryResponse:
        """
        Get chat history for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            ChatHistoryResponse with messages and count
        """
        messages = self.chat_history_store.get(session_id, [])
        
        logger.info(f"Retrieved chat history for session {session_id}. Message count: {len(messages)}")
        
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            message_count=len(messages)
        )
    
    def clear_chat_history(self, session_id: str) -> bool:
        """
        Clear chat history for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session existed and was cleared, False otherwise
        """
        if session_id in self.chat_history_store:
            del self.chat_history_store[session_id]
            logger.info(f"Cleared chat history for session {session_id}")
            return True
        
        logger.warning(f"Attempted to clear non-existent session {session_id}")
        return False
    
    def get_conversation_history(self, session_id: str) -> List[ChatMessage]:
        """
        Get conversation history as a list of ChatMessage objects
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of ChatMessage objects
        """
        return self.chat_history_store.get(session_id, [])
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        return session_id in self.chat_history_store
    
    def get_session_count(self) -> int:
        """
        Get total number of active sessions
        
        Returns:
            Number of active sessions
        """
        return len(self.chat_history_store)
    
    def get_total_messages(self) -> int:
        """
        Get total number of messages across all sessions
        
        Returns:
            Total number of messages
        """
        return sum(len(messages) for messages in self.chat_history_store.values())


# Global chat manager instance
chat_manager = ChatManager()
