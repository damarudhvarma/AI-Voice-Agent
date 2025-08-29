import requests
import json
from typing import Tuple, Optional, Dict, Any, List
from utils.logger import get_logger
from utils.config import Config

logger = get_logger("web_search_service")


class SearchResult:
    """Class to represent a search result"""
    
    def __init__(self, title: str, link: str, snippet: str, source: Optional[str] = None):
        self.title = title
        self.link = link
        self.snippet = snippet
        self.source = source or ""
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'link': self.link,
            'snippet': self.snippet,
            'source': self.source
        }


class WebSearchService:
    """Service for web search using SerpAPI"""
    
    def __init__(self):
        self.api_key = Config.SERP_API_KEY
        self.base_url = "https://serpapi.com/search"
    
    def search(self, query: str, num_results: int = 3) -> Tuple[bool, List[SearchResult], Optional[str]]:
        """
        Perform web search using SerpAPI
        
        Args:
            query: Search query string
            num_results: Number of results to return (default: 3)
            
        Returns:
            Tuple of (success, list_of_results, error_message)
        """
        if not Config.is_api_key_configured('SERP_API_KEY'):
            logger.error("SerpAPI key not configured")
            return False, [], "Web search service is not configured. Please add your SerpAPI key."
        
        if not query.strip():
            logger.error("Empty search query provided")
            return False, [], "Please provide a search query."
        
        try:
            logger.info(f"Performing web search for: {query[:50]}...")
            
            params = {
                'q': query.strip(),
                'api_key': self.api_key,
                'engine': 'google',
                'num': min(num_results, 10),  # Limit to max 10 results
                'gl': 'us',  # Country code
                'hl': 'en'   # Language
            }
            
            response = requests.get(self.base_url, params=params, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors in the response
            if 'error' in data:
                error_msg = data['error']
                logger.error(f"SerpAPI error: {error_msg}")
                return False, [], f"Search API error: {error_msg}"
            
            # Extract organic search results
            organic_results = data.get('organic_results', [])
            
            if not organic_results:
                logger.warning(f"No search results found for query: {query}")
                return False, [], f"No search results found for '{query}'. Try a different search term."
            
            # Parse results
            search_results = []
            for result in organic_results[:num_results]:
                title = result.get('title', 'No title')
                link = result.get('link', '')
                snippet = result.get('snippet', 'No description available')
                source = result.get('displayed_link', '')
                
                search_results.append(SearchResult(
                    title=title,
                    link=link,
                    snippet=snippet,
                    source=source
                ))
            
            logger.info(f"Successfully retrieved {len(search_results)} search results")
            return True, search_results, None
            
        except requests.exceptions.Timeout:
            logger.error("Search request timed out")
            return False, [], "Search request timed out. Please try again."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request error: {str(e)}")
            return False, [], f"Search request failed: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected search error: {str(e)}")
            return False, [], f"An unexpected error occurred during search: {str(e)}"
    
    def format_search_results(self, results: List[SearchResult], query: str) -> str:
        """
        Format search results into a human-readable string
        
        Args:
            results: List of SearchResult objects
            query: Original search query
            
        Returns:
            Formatted string with search results
        """
        if not results:
            return f"No search results found for '{query}'."
        
        formatted_text = f"Here are the top search results for '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_text += f"{i}. **{result.title}**\n"
            formatted_text += f"   {result.snippet}\n"
            if result.source:
                formatted_text += f"   Source: {result.source}\n"
            formatted_text += f"   Link: {result.link}\n\n"
        
        return formatted_text.strip()
    
    def detect_search_intent(self, user_message: str) -> Optional[str]:
        """
        Detect if user message contains a search intent and extract search query
        
        Args:
            user_message: The user's message
            
        Returns:
            Search query if intent detected, None otherwise
        """
        message_lower = user_message.lower().strip()
        
        # Search intent keywords and patterns
        search_patterns = [
            'search for',
            'search',
            'look up',
            'find information about',
            'find',
            'google',
            'what is',
            'who is',
            'tell me about',
            'information about',
            'details about'
        ]
        
        # Check if any search pattern is found
        for pattern in search_patterns:
            if pattern in message_lower:
                # Extract query after the pattern
                if pattern == 'what is' or pattern == 'who is':
                    # For "what is X" or "who is X", the query is everything after the pattern
                    parts = user_message.lower().split(pattern, 1)
                    if len(parts) > 1:
                        query = parts[1].strip().rstrip('?.,!')
                        return query if query else None
                
                elif pattern in ['search for', 'look up', 'find information about', 
                               'tell me about', 'information about', 'details about']:
                    # Extract everything after these patterns
                    parts = user_message.lower().split(pattern, 1)
                    if len(parts) > 1:
                        query = parts[1].strip().rstrip('?.,!')
                        return query if query else None
                
                elif pattern == 'search' and 'search for' not in message_lower:
                    # Handle standalone "search" followed by query
                    if message_lower.startswith('search '):
                        query = user_message[7:].strip().rstrip('?.,!')
                        return query if query else None
                
                elif pattern in ['find', 'google']:
                    # Handle "find X" or "google X"
                    words = user_message.split()
                    for i, word in enumerate(words):
                        if word.lower() == pattern and i + 1 < len(words):
                            query = ' '.join(words[i+1:]).strip().rstrip('?.,!')
                            return query if query else None
        
        # If no specific pattern found but message seems like a search query
        # (contains question words or seems informational)
        question_words = ['how', 'why', 'when', 'where', 'which']
        if any(word in message_lower for word in question_words):
            # Return the entire message as a potential search query
            return user_message.strip().rstrip('?.,!')
        
        return None
    
    def is_configured(self) -> bool:
        """Check if the web search service is properly configured"""
        return Config.is_api_key_configured('SERP_API_KEY')


# Global web search service instance
web_search_service = WebSearchService()
