import requests
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from utils.config import Config
from utils.logger import get_logger

logger = get_logger("news_service")


class NewsArticle:
    """Class to represent a news article"""
    
    def __init__(self, title: str, description: str, url: str, source: str, 
                 published_at: str, url_to_image: Optional[str] = None):
        self.title = title
        self.description = description
        self.url = url
        self.source = source
        self.published_at = published_at
        self.url_to_image = url_to_image
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'source': self.source,
            'published_at': self.published_at,
            'url_to_image': self.url_to_image
        }
    
    def get_formatted_time(self) -> str:
        """Get formatted published time"""
        try:
            # Parse ISO 8601 format from NewsAPI
            dt = datetime.fromisoformat(self.published_at.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            return self.published_at


class NewsService:
    """Service for fetching news using NewsAPI.org"""
    
    def __init__(self):
        self.base_url = "https://newsapi.org/v2"
    
    def _get_current_api_key(self) -> str:
        """Get the current user-provided API key"""
        return Config.get_effective_api_key('NEWS_API_KEY')
    
    def _get_headers(self) -> dict:
        """Get headers with current API key"""
        return {
            'X-API-Key': self._get_current_api_key(),
            'User-Agent': 'AI-Voice-Agent/1.0'
        }
    
    def get_top_headlines(self, country: str = 'us', category: Optional[str] = None, 
                         page_size: int = 5) -> Tuple[bool, List[NewsArticle], Optional[str]]:
        """
        Get top headlines from NewsAPI
        
        Args:
            country: Country code (us, gb, in, etc.)
            category: News category (business, entertainment, general, health, science, sports, technology)
            page_size: Number of articles to return (max 100)
            
        Returns:
            Tuple of (success, list_of_articles, error_message)
        """
        # Check if user has provided an API key or if environment fallback is configured
        if not Config.is_api_key_configured('NEWS_API_KEY'):
            logger.error("NewsAPI key not configured")
            return False, [], "News service requires a NewsAPI key. Please configure your NewsAPI key in settings."
        
        try:
            logger.info(f"Fetching top headlines from NewsAPI (country: {country}, category: {category})")
            
            params = {
                'country': country,
                'pageSize': min(page_size, 100),  # NewsAPI max is 100
                'sortBy': 'publishedAt'
            }
            
            if category:
                params['category'] = category
            
            response = requests.get(
                f"{self.base_url}/top-headlines",
                headers=self._get_headers(),
                params=params,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Check API response status
            if data.get('status') != 'ok':
                error_msg = data.get('message', 'Unknown API error')
                logger.error(f"NewsAPI error: {error_msg}")
                return False, [], f"News API error: {error_msg}"
            
            # Parse articles
            articles = []
            for article_data in data.get('articles', []):
                if not article_data.get('title') or article_data.get('title') == '[Removed]':
                    continue  # Skip removed articles
                
                article = NewsArticle(
                    title=article_data.get('title', '').strip(),
                    description=article_data.get('description', '').strip(),
                    url=article_data.get('url', ''),
                    source=article_data.get('source', {}).get('name', 'Unknown'),
                    published_at=article_data.get('publishedAt', ''),
                    url_to_image=article_data.get('urlToImage')
                )
                articles.append(article)
            
            if not articles:
                logger.warning("No valid articles found in NewsAPI response")
                return False, [], "No news articles available at the moment."
            
            logger.info(f"Successfully retrieved {len(articles)} news articles")
            return True, articles, None
            
        except requests.exceptions.Timeout:
            logger.error("NewsAPI request timed out")
            return False, [], "News request timed out. Please try again."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI request error: {str(e)}")
            return False, [], f"Failed to fetch news: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in NewsAPI: {str(e)}")
            return False, [], f"An unexpected error occurred while fetching news: {str(e)}"
    
    def search_news(self, query: str, page_size: int = 5, language: str = 'en') -> Tuple[bool, List[NewsArticle], Optional[str]]:
        """
        Search for news articles by query
        
        Args:
            query: Search query
            page_size: Number of articles to return
            language: Language code (en, es, fr, etc.)
            
        Returns:
            Tuple of (success, list_of_articles, error_message)
        """
        # Check if user has provided an API key or if environment fallback is configured
        if not Config.is_api_key_configured('NEWS_API_KEY'):
            logger.error("NewsAPI key not configured")
            return False, [], "News service requires a NewsAPI key. Please configure your NewsAPI key in settings."
        
        if not query.strip():
            return False, [], "Please provide a search query."
        
        try:
            logger.info(f"Searching news for: {query[:50]}...")
            
            params = {
                'q': query.strip(),
                'pageSize': min(page_size, 100),
                'language': language,
                'sortBy': 'publishedAt'
            }
            
            response = requests.get(
                f"{self.base_url}/everything",
                headers=self._get_headers(),
                params=params,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            logger.info(f"NewsAPI search response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"NewsAPI search response status field: {data.get('status')}")
            logger.info(f"NewsAPI search total results: {data.get('totalResults', 0)}")
            
            if data.get('status') != 'ok':
                error_msg = data.get('message', 'Unknown API error')
                logger.error(f"NewsAPI search error: {error_msg}")
                return False, [], f"News search error: {error_msg}"
            
            # Parse articles
            articles = []
            for article_data in data.get('articles', []):
                if not article_data.get('title') or article_data.get('title') == '[Removed]':
                    continue
                
                article = NewsArticle(
                    title=article_data.get('title', '').strip(),
                    description=article_data.get('description', '').strip(),
                    url=article_data.get('url', ''),
                    source=article_data.get('source', {}).get('name', 'Unknown'),
                    published_at=article_data.get('publishedAt', ''),
                    url_to_image=article_data.get('urlToImage')
                )
                articles.append(article)
            
            if not articles:
                logger.warning(f"No articles found for search query: {query}")
                return False, [], f"No news articles found for '{query}'. Try a different search term."
            
            logger.info(f"Successfully found {len(articles)} articles for search query")
            return True, articles, None
            
        except requests.exceptions.Timeout:
            logger.error("NewsAPI search request timed out")
            return False, [], "News search timed out. Please try again."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI search request error: {str(e)}")
            return False, [], f"Failed to search news: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in news search: {str(e)}")
            return False, [], f"An unexpected error occurred during news search: {str(e)}"
    
    def format_articles_for_response(self, articles: List[NewsArticle], max_articles: int = 5) -> str:
        """
        Format news articles into a human-readable response
        
        Args:
            articles: List of NewsArticle objects
            max_articles: Maximum number of articles to include
            
        Returns:
            Formatted string with news articles
        """
        if not articles:
            return "No news articles available."
        
        formatted_articles = []
        for i, article in enumerate(articles[:max_articles], 1):
            # Format each article - simple format for better audio readability
            article_text = f"{i}. {article.title}"
            
            if article.source and article.source != 'Unknown':
                article_text += f" (Source: {article.source})"
            
            formatted_articles.append(article_text)
        
        return "\n\n".join(formatted_articles)
    
    def is_configured(self) -> bool:
        """Check if the news service is properly configured"""
        configured = Config.is_api_key_configured('NEWS_API_KEY')
        current_key = self._get_current_api_key()
        logger.info(f"NewsAPI configuration check: configured={configured}, api_key_length={len(current_key) if current_key else 0}")
        return configured


# Global news service instance
news_service = NewsService()
