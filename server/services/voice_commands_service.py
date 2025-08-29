import re
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from utils.config import Config
from utils.logger import get_logger
from services.web_search_service import web_search_service
from services.news_service import news_service

logger = get_logger("voice_commands_service")


class VoiceCommandResult:
    """Class to represent a voice command result"""
    
    def __init__(self, success: bool, response: str, command_type: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.response = response
        self.command_type = command_type
        self.data = data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'response': self.response,
            'command_type': self.command_type,
            'data': self.data
        }


class VoiceCommandsService:
    """Service for handling smart voice commands and shortcuts"""
    
    def __init__(self):
        self.command_patterns = {
            'calculation': [
                r'calculate\s+(.+)',
                r'what(?:\s+is|\'s)\s+(.+?)(?:\s+\?|$)',
                r'solve\s+(.+)',
                r'compute\s+(.+)',
                r'(\d+[\+\-\*\/\%\^\(\)]+.+)',  # Direct math expressions
            ],
            'weather': [
                r'weather\s+(?:in\s+)?(.+)',
                r'what(?:\s+is|\'s)\s+the\s+weather\s+(?:in\s+)?(.+)',
                r'temperature\s+(?:in\s+)?(.+)',
                r'forecast\s+(?:for\s+)?(.+)',
            ],
            'reminder': [
                r'set\s+(?:a\s+)?reminder\s+(?:for\s+)?(.+)',
                r'remind\s+me\s+(?:to\s+)?(.+)',
                r'reminder\s+(.+)',
            ],
            'note': [
                r'(?:create\s+(?:a\s+)?note|take\s+(?:a\s+)?note|note)(?:\s*:)?\s+(.+)',
                r'remember\s+(?:that\s+)?(.+)',
                r'save\s+(?:this\s+)?(?:note\s*:?\s*)?(.+)',
            ],
            'conversion': [
                r'convert\s+(.+)\s+to\s+(.+)',
                r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+(?:to\s+|in\s+)([a-zA-Z]+)',
                r'how\s+many\s+(\w+)\s+(?:is\s+|are\s+)?(\d+(?:\.\d+)?)\s*(\w+)',
            ],
            'currency': [
                r'(\d+(?:\.\d+)?)\s*(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|BTC|ETH)\s+(?:to\s+|in\s+)(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|BTC|ETH)',
                r'convert\s+(\d+(?:\.\d+)?)\s*(dollars?|euros?|pounds?|yen|bitcoin|ethereum)\s+to\s+(\w+)',
                r'exchange\s+rate\s+(.+)\s+to\s+(.+)',
            ],
            'time': [
                r'what\s+time\s+(?:is\s+it\s+)?(?:in\s+)?(.+)',
                r'time\s+(?:in\s+)?(.+)',
                r'current\s+time\s+(?:in\s+)?(.+)',
            ],
            'news': [
                r'(?:what\s+are\s+the\s+)?latest\s+news\s*(?:today|headlines)?',
                r'news\s+(?:today|headlines|latest)',
                r'current\s+news',
                r'today\'?s\s+news',
                r'news\s+updates?',
            ]
        }
        
        # In-memory storage for notes and reminders (can be extended to persistent storage)
        self.notes = []
        self.reminders = []
    
    def detect_command(self, user_input: str) -> Optional[Tuple[str, List[str]]]:
        """
        Detect if user input matches any voice command pattern
        
        Args:
            user_input: Raw user input text
            
        Returns:
            Tuple of (command_type, matched_groups) or None if no match
        """
        user_input_lower = user_input.lower().strip()
        
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, user_input_lower, re.IGNORECASE)
                if match:
                    return command_type, list(match.groups())
        
        return None
    
    def execute_command(self, command_type: str, parameters: List[str], original_input: str) -> VoiceCommandResult:
        """
        Execute a detected voice command
        
        Args:
            command_type: Type of command detected
            parameters: Extracted parameters from the command
            original_input: Original user input for context
            
        Returns:
            VoiceCommandResult with execution result
        """
        logger.info(f"Executing {command_type} command with parameters: {parameters}")
        
        try:
            if command_type == 'calculation':
                return self._handle_calculation(parameters, original_input)
            elif command_type == 'weather':
                return self._handle_weather(parameters)
            elif command_type == 'reminder':
                return self._handle_reminder(parameters)
            elif command_type == 'note':
                return self._handle_note(parameters)
            elif command_type == 'conversion':
                return self._handle_conversion(parameters)
            elif command_type == 'currency':
                return self._handle_currency(parameters)
            elif command_type == 'time':
                return self._handle_time(parameters)
            elif command_type == 'news':
                return self._handle_news(parameters)
            else:
                return VoiceCommandResult(
                    success=False,
                    response=f"Unknown command type: {command_type}",
                    command_type=command_type
                )
        
        except Exception as e:
            logger.error(f"Error executing {command_type} command: {str(e)}")
            return VoiceCommandResult(
                success=False,
                response=f"Sorry, I encountered an error while processing your {command_type} command: {str(e)}",
                command_type=command_type
            )
    
    def _handle_calculation(self, parameters: List[str], original_input: str) -> VoiceCommandResult:
        """Handle mathematical calculations"""
        try:
            if not parameters:
                return VoiceCommandResult(
                    success=False,
                    response="I need a mathematical expression to calculate.",
                    command_type='calculation'
                )
            
            # Extract the mathematical expression
            expression = parameters[0].strip()
            
            # Clean up common spoken math terms
            expression = expression.replace(' plus ', '+')
            expression = expression.replace(' minus ', '-')
            expression = expression.replace(' times ', '*')
            expression = expression.replace(' divided by ', '/')
            expression = expression.replace(' percent of ', '*0.01*')
            expression = expression.replace(' squared', '**2')
            expression = expression.replace(' cubed', '**3')
            expression = expression.replace(' to the power of ', '**')
            expression = expression.replace(' power ', '**')
            expression = expression.replace('x', '*')
            
            # Handle percentage calculations
            if 'percent' in expression or '%' in expression:
                expression = expression.replace(' percent', '*0.01')
                expression = expression.replace('%', '*0.01')
            
            # Remove question marks and other punctuation
            expression = re.sub(r'[?!.,]', '', expression).strip()
            
            # Basic security check - only allow certain characters
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return VoiceCommandResult(
                    success=False,
                    response="Sorry, I can only handle basic mathematical operations (+, -, *, /, parentheses, and numbers).",
                    command_type='calculation'
                )
            
            # Evaluate the expression safely
            try:
                result = eval(expression)
                formatted_result = f"{result:,.2f}" if isinstance(result, float) else f"{result:,}"
                
                return VoiceCommandResult(
                    success=True,
                    response=f"🧮 The answer is {formatted_result}",
                    command_type='calculation',
                    data={'expression': expression, 'result': result}
                )
            
            except (ValueError, SyntaxError, ZeroDivisionError) as e:
                return VoiceCommandResult(
                    success=False,
                    response=f"I couldn't calculate '{expression}'. Please check your math expression.",
                    command_type='calculation'
                )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble processing that calculation.",
                command_type='calculation'
            )
    
    def _handle_weather(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle weather queries using web search"""
        try:
            if not parameters or not parameters[0].strip():
                location = "current location"
            else:
                location = parameters[0].strip()
            
            # Use web search to get weather information
            search_query = f"weather {location} today current temperature"
            
            if web_search_service.is_configured():
                success, search_results, error = web_search_service.search(search_query, num_results=2)
                
                if success and search_results:
                    # Extract weather info from search results
                    weather_info = []
                    for result in search_results:
                        if any(word in result.snippet.lower() for word in ['°', 'temperature', 'weather', 'celsius', 'fahrenheit']):
                            weather_info.append(result.snippet)
                    
                    if weather_info:
                        formatted_weather = "\n".join(weather_info[:2])
                        return VoiceCommandResult(
                            success=True,
                            response=f"🌤️ Weather for {location}:\n{formatted_weather}",
                            command_type='weather',
                            data={'location': location, 'search_results': [r.to_dict() for r in search_results]}
                        )
            
            # Fallback if web search fails or no weather info found
            return VoiceCommandResult(
                success=True,
                response=f"I'd love to check the weather for {location}, but I need access to a weather service. You can ask me to search for 'weather {location}' instead!",
                command_type='weather'
            )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble getting the weather information.",
                command_type='weather'
            )
    
    def _handle_reminder(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle setting reminders"""
        try:
            if not parameters or not parameters[0].strip():
                return VoiceCommandResult(
                    success=False,
                    response="What would you like me to remind you about?",
                    command_type='reminder'
                )
            
            reminder_text = parameters[0].strip()
            
            # Extract time information if present
            time_match = re.search(r'(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)', reminder_text)
            date_match = re.search(r'(?:on\s+)?(\w+day|\d{1,2}\/\d{1,2}|\d{1,2}-\d{1,2})', reminder_text)
            
            reminder_data = {
                'id': len(self.reminders) + 1,
                'text': reminder_text,
                'created_at': datetime.now().isoformat(),
                'time': time_match.group(1) if time_match else None,
                'date': date_match.group(1) if date_match else None,
                'status': 'active'
            }
            
            self.reminders.append(reminder_data)
            
            time_info = ""
            if reminder_data['time']:
                time_info = f" for {reminder_data['time']}"
            if reminder_data['date']:
                time_info += f" on {reminder_data['date']}"
            
            return VoiceCommandResult(
                success=True,
                response=f"⏰ Reminder set{time_info}: {reminder_text}\n(Note: This is stored temporarily - for persistent reminders, consider using your device's built-in reminder app!)",
                command_type='reminder',
                data=reminder_data
            )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble setting that reminder.",
                command_type='reminder'
            )
    
    def _handle_note(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle taking notes"""
        try:
            if not parameters or not parameters[0].strip():
                return VoiceCommandResult(
                    success=False,
                    response="What would you like me to note down?",
                    command_type='note'
                )
            
            note_text = parameters[0].strip()
            
            note_data = {
                'id': len(self.notes) + 1,
                'text': note_text,
                'created_at': datetime.now().isoformat(),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.notes.append(note_data)
            
            return VoiceCommandResult(
                success=True,
                response=f"📝 Note saved: {note_text}\n(Note #{note_data['id']} - stored temporarily in this session)",
                command_type='note',
                data=note_data
            )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble saving that note.",
                command_type='note'
            )
    
    def _handle_conversion(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle unit conversions"""
        try:
            if len(parameters) < 2:
                return VoiceCommandResult(
                    success=False,
                    response="I need both the value and units to convert. Try 'convert 10 miles to kilometers'.",
                    command_type='conversion'
                )
            
            # Common unit conversions
            conversions = {
                # Length
                ('miles', 'kilometers'): lambda x: x * 1.60934,
                ('kilometers', 'miles'): lambda x: x * 0.621371,
                ('feet', 'meters'): lambda x: x * 0.3048,
                ('meters', 'feet'): lambda x: x * 3.28084,
                ('inches', 'centimeters'): lambda x: x * 2.54,
                ('centimeters', 'inches'): lambda x: x * 0.393701,
                
                # Weight
                ('pounds', 'kilograms'): lambda x: x * 0.453592,
                ('kilograms', 'pounds'): lambda x: x * 2.20462,
                
                # Temperature
                ('celsius', 'fahrenheit'): lambda x: (x * 9/5) + 32,
                ('fahrenheit', 'celsius'): lambda x: (x - 32) * 5/9,
                
                # Volume
                ('gallons', 'liters'): lambda x: x * 3.78541,
                ('liters', 'gallons'): lambda x: x * 0.264172,
            }
            
            # Extract value and units
            if len(parameters) == 3:  # "10 miles kilometers" format
                try:
                    value = float(parameters[0])
                    from_unit = parameters[1].lower().rstrip('s')  # Remove plural 's'
                    to_unit = parameters[2].lower().rstrip('s')
                except ValueError:
                    return VoiceCommandResult(
                        success=False,
                        response="Please provide a valid number for conversion.",
                        command_type='conversion'
                    )
            else:
                # Try to parse "convert X Y to Z" format
                text = ' '.join(parameters)
                match = re.search(r'(\d+(?:\.\d+)?)\s*(\w+)\s+(?:to\s+)?(\w+)', text)
                if match:
                    value = float(match.group(1))
                    from_unit = match.group(2).lower().rstrip('s')
                    to_unit = match.group(3).lower().rstrip('s')
                else:
                    return VoiceCommandResult(
                        success=False,
                        response="I couldn't parse that conversion. Try 'convert 10 miles to kilometers'.",
                        command_type='conversion'
                    )
            
            # Handle common unit aliases
            unit_aliases = {
                'km': 'kilometer', 'mi': 'mile', 'ft': 'foot', 'm': 'meter',
                'cm': 'centimeter', 'in': 'inch', 'lb': 'pound', 'kg': 'kilogram',
                'c': 'celsius', 'f': 'fahrenheit', 'gal': 'gallon', 'l': 'liter'
            }
            
            from_unit = unit_aliases.get(from_unit, from_unit)
            to_unit = unit_aliases.get(to_unit, to_unit)
            
            # Find conversion function
            conversion_key = (from_unit, to_unit)
            if conversion_key in conversions:
                result = conversions[conversion_key](value)
                
                return VoiceCommandResult(
                    success=True,
                    response=f"🔄 {value} {from_unit}(s) = {result:.2f} {to_unit}(s)",
                    command_type='conversion',
                    data={'value': value, 'from_unit': from_unit, 'to_unit': to_unit, 'result': result}
                )
            else:
                return VoiceCommandResult(
                    success=False,
                    response=f"Sorry, I don't know how to convert from {from_unit} to {to_unit}. I can handle common conversions like miles/kilometers, pounds/kilograms, celsius/fahrenheit, etc.",
                    command_type='conversion'
                )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble with that conversion.",
                command_type='conversion'
            )
    
    def _handle_currency(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle currency conversions"""
        try:
            # For now, provide basic currency conversion via web search
            # In a production environment, you'd use a currency API like exchangerate-api.com
            
            if len(parameters) < 2:
                return VoiceCommandResult(
                    success=False,
                    response="I need the amount and currencies to convert. Try '100 USD to EUR'.",
                    command_type='currency'
                )
            
            # Use web search for currency conversion
            search_query = f"convert {' '.join(parameters)} exchange rate"
            
            if web_search_service.is_configured():
                success, search_results, error = web_search_service.search(search_query, num_results=2)
                
                if success and search_results:
                    # Look for currency conversion results
                    currency_info = []
                    for result in search_results:
                        if any(word in result.snippet.lower() for word in ['usd', 'eur', 'exchange', 'currency', '$', '€', '£']):
                            currency_info.append(result.snippet)
                    
                    if currency_info:
                        formatted_currency = "\n".join(currency_info[:2])
                        return VoiceCommandResult(
                            success=True,
                            response=f"💱 Currency conversion:\n{formatted_currency}",
                            command_type='currency',
                            data={'search_results': [r.to_dict() for r in search_results]}
                        )
            
            return VoiceCommandResult(
                success=True,
                response=f"💱 For accurate currency conversion, I'd recommend checking a financial website. You can ask me to search for 'exchange rate {' '.join(parameters)}'!",
                command_type='currency'
            )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble with that currency conversion.",
                command_type='currency'
            )
    
    def _handle_time(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle time queries"""
        try:
            if not parameters or not parameters[0].strip():
                location = "local"
                current_time = datetime.now().strftime("%I:%M %p %Z")
            else:
                location = parameters[0].strip()
                # For different time zones, use web search
                search_query = f"current time {location}"
                
                if web_search_service.is_configured():
                    success, search_results, error = web_search_service.search(search_query, num_results=2)
                    
                    if success and search_results:
                        time_info = []
                        for result in search_results:
                            if any(word in result.snippet.lower() for word in ['time', 'clock', 'am', 'pm', ':']):
                                time_info.append(result.snippet)
                        
                        if time_info:
                            formatted_time = "\n".join(time_info[:2])
                            return VoiceCommandResult(
                                success=True,
                                response=f"🕐 Time in {location}:\n{formatted_time}",
                                command_type='time',
                                data={'location': location, 'search_results': [r.to_dict() for r in search_results]}
                            )
                
                # Fallback to local time
                current_time = datetime.now().strftime("%I:%M %p")
            
            return VoiceCommandResult(
                success=True,
                response=f"🕐 Current time: {current_time}",
                command_type='time',
                data={'time': current_time, 'location': location}
            )
        
        except Exception as e:
            return VoiceCommandResult(
                success=False,
                response="Sorry, I had trouble getting the time information.",
                command_type='time'
            )
    
    def _handle_news(self, parameters: List[str]) -> VoiceCommandResult:
        """Handle news queries using NewsAPI.org"""
        try:
            logger.info("Fetching latest news headlines using NewsAPI...")
            
            # Debug logging for NewsAPI configuration
            from utils.config import Config
            logger.info(f"NewsAPI configured: {news_service.is_configured()}")
            logger.info(f"NEWS_API_KEY value: {Config.NEWS_API_KEY[:10]}..." if Config.NEWS_API_KEY else "None")
            logger.info(f"is_api_key_configured result: {Config.is_api_key_configured('NEWS_API_KEY')}")
            
            # Force try NewsAPI first, regardless of configuration check
            logger.info("Attempting to use NewsAPI...")
            try:
                # Skip country-specific search since India returns 0 articles
                # Go directly to global India-related news search
                logger.info("Searching for India-related news globally using NewsAPI...")
                success, articles, error = news_service.search_news(
                    query='India',  # Simplified query more likely to get results
                    page_size=5
                )
                
                # If no India-related articles found, try general world news
                if success and not articles:
                    logger.info("No India-related articles found, trying general world news...")
                    success, articles, error = news_service.get_top_headlines(
                        country='us',  # US has more reliable coverage
                        page_size=5
                    )
                
                logger.info(f"NewsAPI response: success={success}, articles_count={len(articles) if articles else 0}, error={error}")
                
                if success and articles:
                    # Format articles using the news service formatter
                    formatted_news = news_service.format_articles_for_response(articles, max_articles=5)
                    response_text = f"📰 Here are the latest news headlines:\n\n{formatted_news}"
                    
                    logger.info(f"NewsAPI success: returning {len(articles)} articles")
                    logger.info(f"Sample headlines: {[article.title[:50] + '...' if len(article.title) > 50 else article.title for article in articles[:3]]}")
                    
                    return VoiceCommandResult(
                        success=True,
                        response=response_text,
                        command_type='news',
                        data={
                            'articles_count': len(articles),
                            'source': 'newsapi',
                            'method': 'india_search' if articles and 'India' in str(articles[0].title) else 'country_headlines',
                            'articles': [article.to_dict() for article in articles[:5]]
                        }
                    )
                else:
                    logger.warning(f"NewsAPI call failed or returned no articles: {error}")
                    raise Exception(f"NewsAPI failed: {error}")
                    
            except Exception as newsapi_error:
                logger.error(f"NewsAPI error: {newsapi_error}. Falling back to web search...")
                return self._handle_news_enhanced_web_search()
        
        except Exception as e:
            logger.error(f"Error fetching news from NewsAPI: {str(e)}", exc_info=True)
            # Fallback to web search on exception
            logger.info("Falling back to enhanced web search due to NewsAPI error...")
            return self._handle_news_enhanced_web_search()
    
    def _handle_news_enhanced_web_search(self) -> VoiceCommandResult:
        """Enhanced fallback method to get actual news headlines using web search"""
        try:
            logger.info("Using enhanced web search for news headlines...")
            
            if web_search_service.is_configured():
                # Try multiple specific news search queries to get actual headlines
                search_queries = [
                    "breaking news today December 2024 headlines",
                    "latest world news headlines today",
                    "top news stories today current events",
                    "today's major news headlines breaking"
                ]
                
                all_headlines = []
                unique_headlines = set()
                
                for search_query in search_queries:
                    logger.info(f"Searching: {search_query}")
                    success, search_results, error = web_search_service.search(search_query, num_results=3)
                    
                    if success and search_results:
                        for result in search_results:
                            headline = result.title.strip()
                            source = result.source if result.source else "Unknown"
                            
                            # Skip generic website pages and navigation links
                            skip_patterns = [
                                "breaking news, latest news and videos",
                                "latest news headlines",
                                "breaking news updates",
                                "world | latest news",
                                "news | latest",
                                "homepage",
                                "home page",
                                "latest news & updates",
                                "breaking news updates | latest news headlines"
                            ]
                            
                            headline_lower = headline.lower()
                            
                            # Skip if this looks like a website homepage or navigation
                            if any(pattern in headline_lower for pattern in skip_patterns):
                                continue
                            
                            # Skip if headline is too short (likely not a real news headline)
                            if len(headline) < 25:
                                continue
                            
                            # Skip if this headline already exists
                            if headline in unique_headlines:
                                continue
                            
                            # Clean up source name
                            clean_source = source.replace("www.", "").replace(".com", "").replace(".org", "").replace(".net", "").title()
                            
                            unique_headlines.add(headline)
                            all_headlines.append({
                                'title': headline,
                                'source': clean_source,
                                'url': result.link
                            })
                            
                            # Stop if we have enough headlines
                            if len(all_headlines) >= 6:
                                break
                    
                    # Stop searching if we have enough headlines
                    if len(all_headlines) >= 6:
                        break
                
                if all_headlines:
                    # Format the headlines for display
                    formatted_headlines = []
                    for i, item in enumerate(all_headlines[:5], 1):
                        headline_text = f"{i}. **{item['title']}**"
                        if item['source'] and item['source'] != "Unknown":
                            headline_text += f" ({item['source']})"
                        formatted_headlines.append(headline_text)
                    
                    formatted_news = "\n\n".join(formatted_headlines)
                    response_text = f"📰 Here are the latest news headlines:\n\n{formatted_news}"
                    
                    logger.info(f"Enhanced web search found {len(formatted_headlines)} quality headlines")
                    return VoiceCommandResult(
                        success=True,
                        response=response_text,
                        command_type='news',
                        data={
                            'headlines_count': len(formatted_headlines),
                            'source': 'enhanced_web_search',
                            'headlines': all_headlines[:5]
                        }
                    )
                else:
                    # If no quality headlines found, try a simpler approach
                    logger.warning("No quality headlines found, trying simpler search...")
                    return self._handle_news_simple_web_search()
            else:
                return VoiceCommandResult(
                    success=False,
                    response="📰 News service is not configured. Please add your NewsAPI key or SerpAPI key to access latest news.",
                    command_type='news'
                )
        
        except Exception as e:
            logger.error(f"Error in enhanced news web search: {str(e)}")
            return self._handle_news_simple_web_search()
    
    def _handle_news_simple_web_search(self) -> VoiceCommandResult:
        """Simple fallback for news when enhanced search fails"""
        try:
            logger.info("Using simple web search fallback for news...")
            
            if web_search_service.is_configured():
                # Use a more specific search query that should return actual news
                search_query = "news headlines December 2024 breaking latest"
                success, search_results, error = web_search_service.search(search_query, num_results=5)
                
                if success and search_results:
                    # Extract and format whatever headlines we can find
                    news_items = []
                    for i, result in enumerate(search_results, 1):
                        title = result.title.strip()
                        
                        # Basic filtering to avoid homepage links
                        if len(title) > 20 and not any(skip in title.lower() for skip in ["homepage", "latest news and videos", "breaking news updates |"]):
                            source = result.source.replace("www.", "").split(".")[0].title() if result.source else "News Source"
                            news_items.append(f"{i}. {title} ({source})")
                    
                    if news_items:
                        formatted_news = "\n\n".join(news_items)
                        response_text = f"📰 Here are some current news headlines:\n\n{formatted_news}"
                        
                        return VoiceCommandResult(
                            success=True,
                            response=response_text,
                            command_type='news',
                            data={
                                'headlines_count': len(news_items),
                                'source': 'simple_web_search',
                                'method': 'fallback'
                            }
                        )
                
                # Final fallback with a helpful message
                return VoiceCommandResult(
                    success=False,
                    response="📰 I'm having trouble accessing current news headlines. Please check your internet connection or try again later. For the best news experience, please add your NewsAPI key to the .env file.",
                    command_type='news'
                )
            else:
                return VoiceCommandResult(
                    success=False,
                    response="📰 News service is not configured. Please add your NewsAPI key or SerpAPI key to access latest news.",
                    command_type='news'
                )
        
        except Exception as e:
            logger.error(f"Error in simple news web search: {str(e)}")
            return VoiceCommandResult(
                success=False,
                response="📰 I'm having trouble fetching news headlines right now. Please try again later or configure NewsAPI for better reliability.",
                command_type='news'
            )
    
    def get_notes(self) -> List[Dict[str, Any]]:
        """Get all stored notes"""
        return self.notes
    
    def get_reminders(self) -> List[Dict[str, Any]]:
        """Get all stored reminders"""
        return self.reminders
    
    def is_voice_command(self, user_input: str) -> bool:
        """Check if user input is a voice command"""
        return self.detect_command(user_input) is not None


# Global voice commands service instance
voice_commands_service = VoiceCommandsService()
