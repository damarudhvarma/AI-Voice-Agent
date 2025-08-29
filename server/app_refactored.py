from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.exceptions import RequestEntityTooLarge
import os
import json
import time
import base64

# Import our custom modules
from utils.config import Config
from utils.logger import get_logger, setup_logger
from models.schemas import (
    TTSRequest, TTSResponse, TranscriptionResponse, LLMQueryResponse,
    AgentChatResponse, ChatHistoryResponse, HealthCheckResponse,
    FileInfo, ErrorResponse, ErrorType, MessageRole
)
from services.stt_service import stt_service
from services.tts_service import tts_service
from services.llm_service import llm_service
from services.chat_manager import chat_manager
from services.file_service import file_service
from services.voice_commands_service import voice_commands_service

# Setup logging
logger = setup_logger()

# Create Flask app
app = Flask(__name__, template_folder='../client', static_folder='../client', static_url_path='')
CORS(app)
sock = Sock(app)

# Configure app
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file upload size limit exceeded"""
    logger.warning("File upload size limit exceeded")
    return jsonify(ErrorResponse(
        error="File too large. Maximum size is 16MB."
    ).model_dump()), 413


@app.errorhandler(Exception)
def handle_generic_error(e):
    """Handle generic errors"""
    logger.error(f"Unhandled error: {str(e)}")
    return jsonify(ErrorResponse(
        error="Internal server error. Please try again."
    ).model_dump()), 500


@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')


@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files like CSS, JS, images"""
    if filename.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
        return send_from_directory('../client', filename)
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    """Enhanced health check with API status"""
    logger.info("Health check requested")
    
    response = HealthCheckResponse(
        status='healthy',
        message='AI Voice Agent Backend is running!',
        apis=Config.get_api_status(),
        error_handling='enabled'
    )
    
    return jsonify(response.dict())


@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """Upload audio file endpoint"""
    logger.info("Audio upload requested")
    
    if 'audio' not in request.files:
        logger.error("No audio file in request")
        return jsonify(ErrorResponse(error="No audio file part in the request").dict()), 400
    
    file = request.files['audio']
    file_info = file_service.save_audio_file(file)
    
    if file_info is None:
        return jsonify(ErrorResponse(error="Failed to save audio file").dict()), 500
    
    return jsonify(file_info.dict())


@app.route('/api/transcribe/file', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file endpoint"""
    logger.info("Audio transcription requested")
    
    if 'audio' not in request.files:
        logger.error("No audio file in request")
        return jsonify(ErrorResponse(error="No audio file part in the request").dict()), 400
    
    file = request.files['audio']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify(ErrorResponse(error="No selected file").dict()), 400
    
    try:
        # Read the audio file data
        audio_data = file.read()
        
        # Use STT service to transcribe
        success, response, error_type = stt_service.transcribe_audio(audio_data)
        
        if success:
            return jsonify(response.dict())
        else:
            return jsonify(ErrorResponse(error=response.transcript).dict()), 500
            
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return jsonify(ErrorResponse(error=f"Transcription error: {str(e)}").dict()), 500


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """Text-to-speech endpoint"""
    logger.info("TTS requested")
    
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Invalid JSON data").dict()), 400
        
        tts_request = TTSRequest(**data)
        
        # Use TTS service to generate speech
        success, response, error_type = tts_service.generate_speech(tts_request.text)
        
        if success:
            return jsonify(response.dict())
        else:
            return jsonify(ErrorResponse(error=response.fallback_text or "TTS generation failed").dict()), 500
            
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        return jsonify(ErrorResponse(error=f"TTS error: {str(e)}").dict()), 500


@app.route('/api/tts/echo', methods=['POST'])
def tts_echo():
    """Echo bot: Transcribe audio and generate new audio"""
    logger.info("TTS echo requested")
    
    if 'audio' not in request.files:
        logger.error("No audio file in request")
        return jsonify(ErrorResponse(error="No audio file part in the request").dict()), 400
    
    file = request.files['audio']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify(ErrorResponse(error="No selected file").dict()), 400
    
    try:
        # Step 1: Transcribe audio
        audio_data = file.read()
        success, transcription_response, error_type = stt_service.transcribe_audio(audio_data)
        
        if not success:
            return jsonify(ErrorResponse(error=transcription_response.transcript).dict()), 500
        
        transcribed_text = transcription_response.transcript
        
        # Step 2: Generate new audio
        success, tts_response, error_type = tts_service.generate_speech(transcribed_text)
        
        if success and tts_response.audio_url:
            return jsonify({
                'success': True,
                'transcription': transcribed_text,
                'audio_url': tts_response.audio_url,
                'voice_id': Config.MURF_VOICE_ID
            })
        else:
            return jsonify(ErrorResponse(error="Failed to generate audio response").dict()), 500
            
    except Exception as e:
        logger.error(f"TTS echo error: {str(e)}")
        return jsonify(ErrorResponse(error=f"Echo processing error: {str(e)}").dict()), 500


@app.route('/api/llm/query', methods=['POST'])
def llm_query():
    """LLM query endpoint: Transcribe, process with LLM, and generate audio response"""
    logger.info("LLM query requested")
    
    if 'audio' not in request.files:
        logger.error("No audio file in request")
        return jsonify(ErrorResponse(error="No audio file part in the request").dict()), 400
    
    file = request.files['audio']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify(ErrorResponse(error="No selected file").dict()), 400
    
    try:
        # Step 1: Transcribe audio
        audio_data = file.read()
        success, transcription_response, error_type = stt_service.transcribe_audio(audio_data)
        
        if not success:
            return jsonify(ErrorResponse(error=transcription_response.transcript).dict()), 500
        
        transcribed_text = transcription_response.transcript
        
        # Step 2: Generate LLM response
        success, llm_response_text, error_type = llm_service.generate_response(transcribed_text)
        
        if not success:
            return jsonify(ErrorResponse(error=llm_response_text).dict()), 500
        
        # Step 3: Generate audio from LLM response
        success, tts_response, error_type = tts_service.generate_speech(llm_response_text)
        
        if success and tts_response.audio_url:
            response = LLMQueryResponse(
                success=True,
                transcription=transcribed_text,
                llm_response=llm_response_text,
                audio_url=tts_response.audio_url,
                voice_id=Config.MURF_VOICE_ID,
                model=Config.GEMINI_MODEL
            )
            return jsonify(response.dict())
        else:
            return jsonify(ErrorResponse(error="Failed to generate audio response").dict()), 500
            
    except Exception as e:
        logger.error(f"LLM query error: {str(e)}")
        return jsonify(ErrorResponse(error=f"LLM query error: {str(e)}").dict()), 500


@app.route('/api/agent/chat/<session_id>', methods=['POST'])
def agent_chat(session_id):
    """Agent chat endpoint with conversation history"""
    logger.info(f"Agent chat requested for session: {session_id}")
    
    if 'audio' not in request.files:
        logger.error("No audio file in request")
        fallback_response = tts_service._create_fallback_response(ErrorType.GENERAL_ERROR)
        return jsonify({
            'error': 'No audio file provided',
            'fallback_audio': fallback_response.dict()
        }), 400
    
    file = request.files['audio']
    if file.filename == '':
        logger.error("No selected file")
        fallback_response = tts_service._create_fallback_response(ErrorType.GENERAL_ERROR)
        return jsonify({
            'error': 'No audio file selected',
            'fallback_audio': fallback_response.dict()
        }), 400
    
    try:
        # Step 1: Transcribe audio
        audio_data = file.read()
        success, transcription_response, error_type = stt_service.transcribe_audio(audio_data)
        
        if not success:
            logger.warning(f"STT failed: {transcription_response.transcript}")
            fallback_response = tts_service._create_fallback_response(error_type or ErrorType.STT_ERROR)
            return jsonify({
                'success': True,
                'session_id': session_id,
                'user_message': transcription_response.transcript,
                'assistant_response': fallback_response.fallback_text,
                'audio_url': fallback_response.audio_url,
                'message_count': 1,
                'is_fallback': True,
                'error_type': error_type.value if error_type else ErrorType.STT_ERROR.value
            })
        
        transcribed_text = transcription_response.transcript
        
        # Step 2: Add user message to chat history
        chat_manager.add_message(session_id, MessageRole.USER, transcribed_text)
        
        # Step 3: Get conversation history for context
        conversation_history = chat_manager.get_conversation_history(session_id)
        
        # Step 4: Generate LLM response
        success, llm_response_text, error_type = llm_service.generate_response(
            transcribed_text, conversation_history
        )
        
        if not success:
            logger.warning(f"LLM failed: {llm_response_text}")
            llm_response_text = tts_service._create_fallback_response(ErrorType.LLM_ERROR).fallback_text
        
        # Step 5: Add assistant response to chat history
        chat_manager.add_message(session_id, MessageRole.ASSISTANT, llm_response_text)
        
        # Step 6: Generate audio response
        success, tts_response, error_type = tts_service.generate_speech(llm_response_text)
        
        # Step 7: Return response
        response = AgentChatResponse(
            success=True,
            session_id=session_id,
            user_message=transcribed_text,
            assistant_response=llm_response_text,
            audio_url=tts_response.audio_url,
            fallback_text=tts_response.fallback_text,
            message_count=len(chat_manager.get_conversation_history(session_id)),
            voice_id=Config.MURF_VOICE_ID,
            model=Config.GEMINI_MODEL,
            is_fallback=tts_response.is_fallback,
            error_type=tts_response.error_type.value if tts_response.error_type else None
        )
        
        return jsonify(response.dict())
        
    except Exception as e:
        logger.error(f"Agent chat error: {str(e)}")
        fallback_response = tts_service._create_fallback_response(ErrorType.GENERAL_ERROR)
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user_message': '[Error processing request]',
            'assistant_response': fallback_response.fallback_text,
            'audio_url': fallback_response.audio_url,
            'message_count': 1,
            'is_fallback': True,
            'error_type': ErrorType.GENERAL_ERROR.value
        })


@app.route('/api/agent/chat/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a specific session"""
    logger.info(f"Chat history requested for session: {session_id}")
    
    response = chat_manager.get_chat_history(session_id)
    return jsonify(response.dict())


@app.route('/api/agent/chat/<session_id>/clear', methods=['DELETE'])
def clear_chat_history(session_id):
    """Clear chat history for a specific session"""
    logger.info(f"Clear chat history requested for session: {session_id}")
    
    success = chat_manager.clear_chat_history(session_id)
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Chat history cleared' if success else 'Session not found'
    })


@app.route('/api/voice-commands', methods=['GET'])
def get_voice_commands():
    """Get list of available voice commands and their patterns"""
    logger.info("Voice commands list requested")
    
    command_info = {
        'commands': {
            'calculation': {
                'description': 'Perform mathematical calculations',
                'examples': [
                    'Calculate 15 + 25',
                    'What is 50% of 200?',
                    'Solve 10 squared',
                    'Compute 100 divided by 5'
                ],
                'patterns': ['calculate X', 'what is X', 'solve X', 'compute X']
            },
            'weather': {
                'description': 'Get weather information for locations',
                'examples': [
                    'Weather in New York',
                    'What\'s the weather in London?',
                    'Temperature in Tokyo',
                    'Forecast for Miami'
                ],
                'patterns': ['weather in X', 'temperature in X', 'forecast for X']
            },
            'reminder': {
                'description': 'Set reminders (temporary, session-based)',
                'examples': [
                    'Set a reminder for 3 PM',
                    'Remind me to call John',
                    'Reminder: Meeting tomorrow'
                ],
                'patterns': ['set reminder for X', 'remind me to X', 'reminder X']
            },
            'note': {
                'description': 'Take notes (temporary, session-based)',
                'examples': [
                    'Note: Important meeting details',
                    'Remember that client prefers email',
                    'Save this: Project deadline is Friday'
                ],
                'patterns': ['note: X', 'remember X', 'save this: X']
            },
            'conversion': {
                'description': 'Convert between different units',
                'examples': [
                    'Convert 10 miles to kilometers',
                    '5 feet to meters',
                    '100 pounds to kilograms',
                    'Convert 32 Fahrenheit to Celsius'
                ],
                'patterns': ['convert X to Y', 'X to Y']
            },
            'currency': {
                'description': 'Convert between currencies',
                'examples': [
                    '100 USD to EUR',
                    'Convert 50 dollars to pounds',
                    'Exchange rate USD to JPY'
                ],
                'patterns': ['X USD to EUR', 'convert X dollars to Y', 'exchange rate X to Y']
            },
            'time': {
                'description': 'Get current time for different locations',
                'examples': [
                    'What time is it in India?',
                    'Time in London',
                    'Current time in Tokyo'
                ],
                'patterns': ['what time is it in X', 'time in X', 'current time in X']
            },
            'news': {
                'description': 'Get latest news headlines and updates using NewsAPI.org',
                'examples': [
                    'What are the latest news today?',
                    'Latest news headlines',
                    'Current news updates',
                    'Today\'s news'
                ],
                'patterns': ['latest news today', 'news headlines', 'current news', 'today\'s news'],
                'note': 'Uses NewsAPI.org for reliable news data with fallback to web search'
            }
        },
        'notes': [
            'Voice commands are processed before regular chat responses',
            'Some commands may require additional API keys (weather, currency, news)',
            'News uses NewsAPI.org for reliable data with web search fallback',
            'Notes and reminders are stored temporarily for the session',
            'Math calculations support basic operations: +, -, *, /, %, ^, ()'
        ]
    }
    
    return jsonify(command_info)


@app.route('/api/voice-commands/execute', methods=['POST'])
def execute_voice_command():
    """Execute a voice command directly"""
    logger.info("Voice command execution requested")
    
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify(ErrorResponse(error="Missing 'command' in request").dict()), 400
        
        command_text = data['command'].strip()
        if not command_text:
            return jsonify(ErrorResponse(error="Empty command provided").dict()), 400
        
        # Detect and execute voice command
        command_detection = voice_commands_service.detect_command(command_text)
        
        if not command_detection:
            return jsonify({
                'success': False,
                'message': 'No voice command detected in the input',
                'input': command_text,
                'suggestion': 'Try phrases like "calculate 5+5", "weather in London", or "convert 10 miles to km"'
            })
        
        command_type, parameters = command_detection
        result = voice_commands_service.execute_command(command_type, parameters, command_text)
        
        return jsonify({
            'success': result.success,
            'command_type': result.command_type,
            'response': result.response,
            'data': result.data,
            'input': command_text
        })
        
    except Exception as e:
        logger.error(f"Voice command execution error: {str(e)}")
        return jsonify(ErrorResponse(error=f"Command execution error: {str(e)}").dict()), 500


@app.route('/api/voice-commands/notes', methods=['GET'])
def get_voice_command_notes():
    """Get all notes taken via voice commands"""
    logger.info("Voice command notes requested")
    
    notes = voice_commands_service.get_notes()
    return jsonify({
        'success': True,
        'notes': notes,
        'count': len(notes)
    })


@app.route('/api/voice-commands/reminders', methods=['GET'])
def get_voice_command_reminders():
    """Get all reminders set via voice commands"""
    logger.info("Voice command reminders requested")
    
    reminders = voice_commands_service.get_reminders()
    return jsonify({
        'success': True,
        'reminders': reminders,
        'count': len(reminders)
    })


@app.route('/api/news/test', methods=['GET'])
def test_news_api():
    """Test NewsAPI configuration and fetch sample headlines"""
    try:
        from services.news_service import news_service
        
        # Check configuration
        is_configured = news_service.is_configured()
        api_key = Config.get_effective_api_key('NEWS_API_KEY')
        api_key_length = len(api_key) if api_key else 0
        
        response_data = {
            'newsapi_configured': is_configured,
            'api_key_length': api_key_length,
            'api_key_preview': f"{api_key[:8]}..." if api_key and len(api_key) > 8 else "Not set"
        }
        
        if is_configured:
            # Test the same logic as the voice command
            # First try Indian headlines
            success, articles, error = news_service.get_top_headlines(country='in', page_size=5)
            
            # If no articles, search globally for India-related news
            if success and not articles:
                success, articles, error = news_service.search_news(
                    query='India OR Indian OR Modi OR Delhi OR Mumbai',
                    page_size=5
                )
                response_data['method'] = 'global_india_search'
            else:
                response_data['method'] = 'india_headlines'
            
            response_data['test_call'] = {
                'success': success,
                'articles_count': len(articles) if articles else 0,
                'error': error
            }
            
            if success and articles:
                response_data['sample_headlines'] = [
                    {'title': article.title, 'source': article.source} 
                    for article in articles[:5]
                ]
                
                # Show what the UI will display
                formatted_response = news_service.format_articles_for_response(articles, max_articles=5)
                response_data['ui_response'] = f"📰 Here are the latest news headlines:\n\n{formatted_response}"
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error testing NewsAPI: {str(e)}")
        return jsonify({
            'error': str(e),
            'newsapi_configured': False
        }), 500


@app.route('/api/config/api-keys', methods=['GET'])
def get_api_key_config():
    """Get current API key configuration status"""
    logger.info("API key configuration status requested")
    
    try:
        # Get API key sources and status
        sources = Config.get_api_key_sources()
        user_keys = Config.get_all_user_api_keys()
        
        # Create response with masked keys for security
        response = {
            'success': True,
            'api_keys': {},
            'user_provided_count': len(user_keys),
            'total_configured': sum(1 for info in sources.values() if info['configured'])
        }
        
        # Add information about each API key
        for key_name, info in sources.items():
            effective_key = Config.get_effective_api_key(key_name)
            
            response['api_keys'][key_name] = {
                'configured': info['configured'],
                'source': info['source'],
                'has_user_key': key_name in user_keys,
                'preview': f"{effective_key[:8]}..." if effective_key and len(effective_key) > 8 else "Not set",
                'length': len(effective_key) if effective_key else 0
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting API key configuration: {str(e)}")
        return jsonify(ErrorResponse(error=f"Failed to get API configuration: {str(e)}").dict()), 500


@app.route('/api/config/api-keys', methods=['POST'])
def set_api_key_config():
    """Set user-provided API keys"""
    logger.info("API key configuration update requested")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Invalid JSON data").dict()), 400
        
        api_keys = data.get('api_keys', {})
        if not isinstance(api_keys, dict):
            return jsonify(ErrorResponse(error="api_keys must be a dictionary").dict()), 400
        
        # Validate API key names
        valid_keys = {'ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY', 'SERP_API_KEY', 
                      'OPENWEATHER_API_KEY', 'EXCHANGE_RATE_API_KEY', 'NEWS_API_KEY'}
        
        for key_name in api_keys.keys():
            if key_name not in valid_keys:
                return jsonify(ErrorResponse(error=f"Invalid API key name: {key_name}").dict()), 400
        
        # Set the API keys
        Config.set_multiple_user_api_keys(api_keys)
        
        # Services now get API keys dynamically on each request - no need to reconfigure
        
        # Get updated status
        sources = Config.get_api_key_sources()
        user_keys = Config.get_all_user_api_keys()
        
        response = {
            'success': True,
            'message': 'API keys updated successfully',
            'updated_keys': list(api_keys.keys()),
            'user_provided_count': len(user_keys),
            'total_configured': sum(1 for info in sources.values() if info['configured']),
            'services_reinitialized': True
        }
        
        logger.info(f"API keys updated: {list(api_keys.keys())}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error setting API key configuration: {str(e)}")
        return jsonify(ErrorResponse(error=f"Failed to set API configuration: {str(e)}").dict()), 500


@app.route('/api/config/api-keys/clear', methods=['DELETE'])
def clear_api_key_config():
    """Clear all user-provided API keys"""
    logger.info("API key configuration clear requested")
    
    try:
        # Clear user-provided keys
        Config.clear_user_api_keys()
        
        # Services now get API keys dynamically on each request - no need to reconfigure
        
        response = {
            'success': True,
            'message': 'All user-provided API keys cleared',
            'services_reinitialized': True
        }
        
        logger.info("All user-provided API keys cleared")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error clearing API key configuration: {str(e)}")
        return jsonify(ErrorResponse(error=f"Failed to clear API configuration: {str(e)}").dict()), 500


@app.route('/api/config/validate-mandatory', methods=['GET'])
def validate_mandatory_api_keys():
    """Validate that all mandatory API keys are provided by user"""
    logger.info("Mandatory API key validation requested")
    
    try:
        mandatory_keys = ['ASSEMBLYAI_API_KEY', 'GEMINI_API_KEY', 'MURF_API_KEY']
        missing_keys = []
        
        for key_name in mandatory_keys:
            if not Config.is_api_key_configured(key_name):
                missing_keys.append(key_name)
        
        is_valid = len(missing_keys) == 0
        
        response = {
            'success': True,
            'is_valid': is_valid,
            'missing_keys': missing_keys,
            'message': 'All mandatory API keys configured' if is_valid else f'Missing API keys: {", ".join(missing_keys)}'
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error validating mandatory API keys: {str(e)}")
        return jsonify(ErrorResponse(error=f"Validation error: {str(e)}").dict()), 500


@app.route('/api/config/api-keys/test', methods=['POST'])
def test_api_key():
    """Test a specific API key"""
    logger.info("API key test requested")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(error="Invalid JSON data").dict()), 400
        
        key_name = data.get('key_name')
        key_value = data.get('key_value', '').strip()
        
        if not key_name or not key_value:
            return jsonify(ErrorResponse(error="key_name and key_value are required").dict()), 400
        
        # Temporarily set the key for testing
        original_key = Config.get_user_api_key(key_name)
        Config.set_user_api_key(key_name, key_value)
        
        try:
            # Test the API key based on the service
            if key_name == 'ASSEMBLYAI_API_KEY':
                # Test AssemblyAI by checking if we can configure it
                import assemblyai as aai
                aai.settings.api_key = key_value
                result = {'success': True, 'message': 'AssemblyAI key appears valid'}
                
            elif key_name == 'GEMINI_API_KEY':
                # Test Gemini by configuring it
                import google.generativeai as genai
                genai.configure(api_key=key_value)
                result = {'success': True, 'message': 'Gemini key appears valid'}
                
            elif key_name == 'MURF_API_KEY':
                # Test Murf by checking key format
                if len(key_value) > 20:
                    result = {'success': True, 'message': 'Murf key format appears valid'}
                else:
                    result = {'success': False, 'message': 'Murf key appears too short'}
                    
            elif key_name == 'NEWS_API_KEY':
                # Test NewsAPI with a simple request
                import requests
                response = requests.get(
                    'https://newsapi.org/v2/top-headlines',
                    headers={'X-API-Key': key_value},
                    params={'country': 'us', 'pageSize': 1},
                    timeout=5
                )
                if response.status_code == 200:
                    result = {'success': True, 'message': 'NewsAPI key is valid'}
                else:
                    result = {'success': False, 'message': f'NewsAPI test failed: {response.status_code}'}
                    
            else:
                result = {'success': True, 'message': 'Key format appears valid (no specific test available)'}
                
        except Exception as test_error:
            result = {'success': False, 'message': f'API test failed: {str(test_error)}'}
        
        finally:
            # Restore original key
            if original_key:
                Config.set_user_api_key(key_name, original_key)
            else:
                Config._user_api_keys.pop(key_name, None)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing API key: {str(e)}")
        return jsonify(ErrorResponse(error=f"Failed to test API key: {str(e)}").dict()), 500


# WebSocket endpoint for real-time audio streaming with complete AI pipeline
@sock.route('/ws/audio')
def websocket_audio(ws):
    """
    Production WebSocket endpoint for complete AI voice agent pipeline:
    1. Receives audio data from client
    2. Transcribes audio using STT service
    3. Processes transcription with LLM service
    4. Generates audio response with TTS service
    5. Streams base64 audio back to client
    6. Maintains chat history per session
    """
    import assemblyai as aai
    import io
    import wave
    import tempfile
    
    logger.info("[WebSocket] AI Voice Agent connection established")
    
    # Initialize AssemblyAI transcriber
    aai.settings.api_key = Config.get_effective_api_key('ASSEMBLYAI_API_KEY')
    transcriber = None
    
    if Config.is_api_key_configured('ASSEMBLYAI_API_KEY'):
        try:
            transcriber = aai.Transcriber()
            logger.info("[WebSocket] AssemblyAI transcriber initialized successfully")
        except Exception as e:
            logger.error(f"[WebSocket] Failed to initialize AssemblyAI transcriber: {str(e)}")
            transcriber = None
    else:
        logger.warning("[WebSocket] AssemblyAI API key not configured - transcription disabled")
    
    # Generate unique session ID for this connection
    session_id = f"ws_session_{int(time.time())}_{int(time.time() * 1000) % 1000}"
    current_file_path = None
    audio_chunks = []
    transcription_buffer = []
    last_transcription_time = 0
    transcription_interval = 1.0  # Transcribe every 1 second for faster response
    
    # Send connection status with session info
    ws.send(json.dumps({
        'type': 'connection_established',
        'session_id': session_id,
        'message': 'AI Voice Agent ready',
        'apis_configured': Config.get_api_status()
    }))
    
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
            
            # Try to parse as JSON first (for metadata)
            try:
                json_data = json.loads(data)
                if json_data.get('type') == 'start':
                    # Start new recording session
                    timestamp = int(time.time())
                    filename = f"ws_audio_{session_id}_{timestamp}.wav"
                    current_file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                    audio_chunks = []
                    transcription_buffer = []
                    last_transcription_time = time.time()
                    
                    logger.info(f"[WebSocket] Starting new recording: {filename}")
                    ws.send(json.dumps({
                        'type': 'status',
                        'message': 'Recording started',
                        'filename': filename
                    }))
                    continue
                elif json_data.get('type') == 'stop':
                    # Stop recording and save file
                    if current_file_path and audio_chunks:
                        try:
                            # Combine all audio chunks
                            combined_audio = b''.join(audio_chunks)
                            
                            # Save audio file
                            with open(current_file_path, 'wb') as f:
                                f.write(combined_audio)
                            file_size = os.path.getsize(current_file_path)
                            logger.info(f"[WebSocket] Recording saved: {current_file_path} ({file_size} bytes)")
                            
                            # Final transcription of complete audio
                            if transcriber:
                                try:
                                    logger.info("[WebSocket] Performing final transcription...")
                                    transcript = transcriber.transcribe(current_file_path)
                                    
                                    if transcript.status == aai.TranscriptStatus.completed:
                                        logger.info(f"🎤 FINAL TRANSCRIPTION: {transcript.text}")
                                        ws.send(json.dumps({
                                            'type': 'final_transcription',
                                            'transcript': transcript.text,
                                            'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None
                                        }))
                                        
                                        # Process complete transcription through AI pipeline
                                        if Config.is_api_key_configured('GEMINI_API_KEY'):
                                            try:
                                                logger.info("🤖 Processing complete AI pipeline...")
                                                
                                                # Step 1: Add user message to chat history
                                                chat_manager.add_message(session_id, MessageRole.USER, transcript.text)
                                                
                                                # Step 2: Get conversation history for context
                                                conversation_history = chat_manager.get_conversation_history(session_id)
                                                
                                                # Step 3: Generate LLM streaming response with parallel TTS generation
                                                accumulated_response = ""
                                                tts_threshold = 30  # Start TTS when we have 30 characters
                                                tts_started = False
                                                logger.info("🔄 Starting optimized LLM streaming with parallel TTS...")
                                                
                                                for chunk in llm_service.generate_streaming_response(transcript.text, conversation_history):
                                                    accumulated_response += chunk
                                                    
                                                    # Send each chunk to client immediately
                                                    ws.send(json.dumps({
                                                        'type': 'llm_stream_chunk',
                                                        'chunk': chunk,
                                                        'is_complete': False,
                                                        'session_id': session_id
                                                    }))
                                                    
                                                    # Start TTS early when we have enough text for a meaningful response
                                                    if not tts_started and len(accumulated_response.strip()) >= tts_threshold:
                                                        # Start TTS generation in parallel (non-blocking)
                                                        import threading
                                                        def generate_early_tts():
                                                            # Generate quick audio for the first part
                                                            first_sentence = accumulated_response.split('.')[0] + '.'
                                                            if len(first_sentence) > 10:
                                                                success, base64_audio, error_type = tts_service.generate_fast_base64_audio(first_sentence)
                                                                if success:
                                                                    # Send immediate audio chunk
                                                                    ws.send(json.dumps({
                                                                        'type': 'early_audio_chunk',
                                                                        'audio_base64': base64_audio,
                                                                        'text_part': first_sentence,
                                                                        'session_id': session_id
                                                                    }))
                                                                    logger.info("🚀 Early audio chunk sent")
                                                        
                                                        threading.Thread(target=generate_early_tts, daemon=True).start()
                                                        tts_started = True
                                                        logger.info("🚀 Started parallel TTS generation")
                                                
                                                # Step 4: Add assistant response to chat history
                                                chat_manager.add_message(session_id, MessageRole.ASSISTANT, accumulated_response)
                                                
                                                # Send completion signal with conversation info
                                                message_count = len(chat_manager.get_conversation_history(session_id))
                                                ws.send(json.dumps({
                                                    'type': 'llm_stream_chunk',
                                                    'chunk': '',
                                                    'is_complete': True,
                                                    'full_response': accumulated_response,
                                                    'session_id': session_id,
                                                    'message_count': message_count
                                                }))
                                                
                                                logger.info(f"✅ LLM streaming response completed: {accumulated_response[:50]}...")
                                                
                                                # Step 5: Generate complete audio response (if not already started)
                                                logger.info(f"🎵 Generating complete audio response...")
                                                
                                                success, base64_chunks, error_type = tts_service.generate_streaming_base64_audio(accumulated_response, chunk_size=256)
                                                
                                                if success:
                                                    logger.info(f"🎵 Audio generated successfully - {len(base64_chunks)} chunks")
                                                    
                                                    # Send streaming base64 audio chunks to client via WebSocket
                                                    for i, chunk in enumerate(base64_chunks):
                                                        ws.send(json.dumps({
                                                            'type': 'murf_base64_audio_chunk',
                                                            'chunk': chunk,
                                                            'chunk_index': i,
                                                            'total_chunks': len(base64_chunks),
                                                            'is_complete': False,
                                                            'text': accumulated_response,
                                                            'session_id': session_id
                                                        }))
                                                    
                                                    # Send completion signal
                                                    ws.send(json.dumps({
                                                        'type': 'murf_base64_audio_chunk',
                                                        'chunk': '',
                                                        'chunk_index': len(base64_chunks),
                                                        'total_chunks': len(base64_chunks),
                                                        'is_complete': True,
                                                        'text': accumulated_response,
                                                        'session_id': session_id
                                                    }))
                                                    
                                                    # Send complete conversation update
                                                    ws.send(json.dumps({
                                                        'type': 'conversation_complete',
                                                        'user_message': transcript.text,
                                                        'assistant_response': accumulated_response,
                                                        'session_id': session_id,
                                                        'message_count': message_count,
                                                        'audio_generated': True
                                                    }))
                                                    
                                                    logger.info("✅ Complete AI pipeline processing finished")
                                                else:
                                                    logger.warning(f"⚠️ Failed to generate audio: {error_type}")
                                                    # Create fallback response
                                                    fallback_response = tts_service._create_fallback_response(error_type or ErrorType.TTS_ERROR)
                                                    ws.send(json.dumps({
                                                        'type': 'audio_fallback',
                                                        'error': f'Audio generation failed: {error_type}',
                                                        'fallback_text': fallback_response.fallback_text,
                                                        'session_id': session_id
                                                    }))
                                                
                                            except Exception as e:
                                                logger.error(f"⚠️ AI pipeline error: {str(e)}")
                                                ws.send(json.dumps({
                                                    'type': 'pipeline_error',
                                                    'error': f'AI pipeline error: {str(e)}',
                                                    'session_id': session_id
                                                }))
                                        else:
                                            logger.warning("⚠️ Gemini API key not configured - AI pipeline disabled")
                                            ws.send(json.dumps({
                                                'type': 'pipeline_error',
                                                'error': 'Gemini API key not configured',
                                                'session_id': session_id
                                            }))
                                    else:
                                        logger.error(f"[WebSocket] Final transcription failed: {transcript.error}")
                                except Exception as e:
                                    logger.error(f"[WebSocket] Final transcription error: {str(e)}")
                            else:
                                logger.warning("[WebSocket] No transcriber available for final transcription")
                                
                        except Exception as e:
                            logger.error(f"[WebSocket] Error saving audio file: {str(e)}")
                        
                        ws.send(json.dumps({
                            'type': 'status',
                            'message': 'Recording saved',
                            'filename': os.path.basename(current_file_path),
                            'size': file_size if 'file_size' in locals() else 0
                        }))
                    else:
                        ws.send(json.dumps({
                            'type': 'error',
                            'message': 'No audio data to save'
                        }))
                    continue
                elif json_data.get('type') == 'ping':
                    # Keep-alive ping
                    ws.send(json.dumps({'type': 'pong'}))
                    continue
            except json.JSONDecodeError:
                # Not JSON, treat as binary audio data
                pass
            
            # Handle binary audio data
            try:
                # Try to decode as base64 if it's a string
                if isinstance(data, str):
                    # Check if it looks like base64
                    if len(data) > 100 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in data):
                        audio_data = base64.b64decode(data)
                    else:
                        # Not base64, skip
                        continue
                else:
                    # Already binary data
                    audio_data = data
                
                # Store the audio chunk
                audio_chunks.append(audio_data)
                transcription_buffer.append(audio_data)
                
                current_time = time.time()
                logger.debug(f"[WebSocket] Received audio chunk: {len(audio_data)} bytes (total: {sum(len(chunk) for chunk in audio_chunks)} bytes)")
                
                # Perform real-time transcription every few seconds
                if (transcriber and 
                    transcription_buffer and 
                    current_time - last_transcription_time >= transcription_interval):
                    
                    try:
                        logger.info("[WebSocket] Performing real-time transcription...")
                        
                        # Create temporary file for transcription
                        combined_audio = b''.join(transcription_buffer)
                        temp_file = os.path.join(Config.UPLOAD_FOLDER, f"temp_transcription_{session_id}.wav")
                        with open(temp_file, 'wb') as f:
                            f.write(combined_audio)
                        
                        transcript = transcriber.transcribe(temp_file)
                        
                        # Clean up temporary file
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                        
                        if transcript.status == aai.TranscriptStatus.completed:
                            logger.info(f"🎤 REAL-TIME TRANSCRIPTION: {transcript.text}")
                            ws.send(json.dumps({
                                'type': 'transcription',
                                'transcript': transcript.text,
                                'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None,
                                'timestamp': current_time
                            }))
                        else:
                            logger.warning(f"[WebSocket] Real-time transcription failed: {transcript.error}")
                        
                        # Clear buffer after transcription
                        transcription_buffer = []
                        last_transcription_time = current_time
                        
                    except Exception as e:
                        logger.error(f"[WebSocket] Real-time transcription error: {str(e)}")
                
                # Send acknowledgment
                ws.send(json.dumps({
                    'type': 'chunk_received',
                    'chunk_size': len(audio_data),
                    'total_size': sum(len(chunk) for chunk in audio_chunks)
                }))
                
            except Exception as e:
                logger.error(f"[WebSocket] Error processing audio chunk: {str(e)}")
                ws.send(json.dumps({
                    'type': 'error',
                    'message': f'Error processing audio: {str(e)}'
                }))
                
    except Exception as e:
        logger.error(f"[WebSocket] Connection error: {str(e)}")
    finally:
        logger.info("[WebSocket] Audio streaming connection closed")


# WebSocket endpoint for turn detection
@sock.route('/ws/turn-detection')
def websocket_turn_detection(ws):
    """
    WebSocket endpoint for real-time turn detection using AssemblyAI streaming API
    Detects when user stops talking and sends turn end notifications to client
    """
    import assemblyai as aai
    
    logger.info("[Turn Detection] Connection established")
    
    # Initialize AssemblyAI transcriber
    aai.settings.api_key = Config.get_effective_api_key('ASSEMBLYAI_API_KEY')
    
    if not Config.is_api_key_configured('ASSEMBLYAI_API_KEY'):
        logger.warning("[Turn Detection] AssemblyAI API key not configured - turn detection disabled")
        ws.send(json.dumps({
            'type': 'error',
            'message': 'AssemblyAI API key not configured'
        }))
        return
    
    # Generate unique session ID for this connection
    session_id = f"turn_detection_{int(time.time())}_{int(time.time() * 1000) % 1000}"
    
    # Turn detection variables
    current_transcript = ""
    last_speech_time = None
    turn_timeout = 1.5  # Seconds of silence to consider turn ended (reduced for faster response)
    is_speaking = False
    audio_chunks = []
    transcription_buffer = []
    last_transcription_time = 0
    transcription_interval = 0.5  # Transcribe every 0.5 seconds for faster turn detection
    
    def send_turn_end_notification():
        """Send turn end notification to client"""
        nonlocal current_transcript, is_speaking
        if is_speaking and current_transcript.strip():
            logger.info(f"[Turn Detection] 🎤 Turn ended: '{current_transcript}'")
            ws.send(json.dumps({
                'type': 'turn_end',
                'transcript': current_transcript,
                'timestamp': time.time(),
                'session_id': session_id
            }))
            
            # Process complete turn through AI pipeline
            if Config.is_api_key_configured('GEMINI_API_KEY'):
                try:
                    logger.info("[Turn Detection] 🤖 Processing complete AI pipeline...")
                    
                    # Step 1: Add user message to chat history
                    chat_manager.add_message(session_id, MessageRole.USER, current_transcript)
                    
                    # Step 2: Get conversation history for context
                    conversation_history = chat_manager.get_conversation_history(session_id)
                    
                    # Step 3: Generate LLM streaming response with context
                    accumulated_response = ""
                    logger.info("[Turn Detection] 🔄 Starting LLM streaming response with conversation context...")
                    
                    for chunk in llm_service.generate_streaming_response(current_transcript, conversation_history):
                        accumulated_response += chunk
                        # Send each chunk to client
                        ws.send(json.dumps({
                            'type': 'llm_stream_chunk',
                            'chunk': chunk,
                            'is_complete': False,
                            'session_id': session_id
                        }))
                    
                    # Step 4: Add assistant response to chat history
                    chat_manager.add_message(session_id, MessageRole.ASSISTANT, accumulated_response)
                    
                    # Send completion signal with conversation info
                    message_count = len(chat_manager.get_conversation_history(session_id))
                    ws.send(json.dumps({
                        'type': 'llm_stream_chunk',
                        'chunk': '',
                        'is_complete': True,
                        'full_response': accumulated_response,
                        'session_id': session_id,
                        'message_count': message_count
                    }))
                    
                    logger.info(f"[Turn Detection] ✅ LLM streaming response completed: {accumulated_response[:100]}...")
                    
                    # Step 5: Generate streaming base64 audio from LLM response using Murf
                    logger.info(f"[Turn Detection] 🎵 Generating streaming audio response...")
                    
                    success, base64_chunks, error_type = tts_service.generate_streaming_base64_audio(accumulated_response, chunk_size=512)
                    
                    if success:
                        logger.info(f"[Turn Detection] 🎵 Audio generated successfully - {len(base64_chunks)} chunks")
                        
                        # Send streaming base64 audio chunks to client via WebSocket
                        for i, chunk in enumerate(base64_chunks):
                            ws.send(json.dumps({
                                'type': 'murf_base64_audio_chunk',
                                'chunk': chunk,
                                'chunk_index': i,
                                'total_chunks': len(base64_chunks),
                                'is_complete': False,
                                'text': accumulated_response,
                                'session_id': session_id
                            }))
                        
                        # Send completion signal
                        ws.send(json.dumps({
                            'type': 'murf_base64_audio_chunk',
                            'chunk': '',
                            'chunk_index': len(base64_chunks),
                            'total_chunks': len(base64_chunks),
                            'is_complete': True,
                            'text': accumulated_response,
                            'session_id': session_id
                        }))
                        
                        # Send complete conversation update
                        ws.send(json.dumps({
                            'type': 'conversation_complete',
                            'user_message': current_transcript,
                            'assistant_response': accumulated_response,
                            'session_id': session_id,
                            'message_count': message_count,
                            'audio_generated': True
                        }))
                        
                        logger.info("[Turn Detection] ✅ Complete AI pipeline processing finished")
                    else:
                        logger.warning(f"[Turn Detection] ⚠️ Failed to generate audio: {error_type}")
                        # Create fallback response
                        fallback_response = tts_service._create_fallback_response(error_type or ErrorType.TTS_ERROR)
                        ws.send(json.dumps({
                            'type': 'audio_fallback',
                            'error': f'Audio generation failed: {error_type}',
                            'fallback_text': fallback_response.fallback_text,
                            'session_id': session_id
                        }))
                    
                except Exception as e:
                    logger.error(f"[Turn Detection] ⚠️ AI pipeline error: {str(e)}")
                    ws.send(json.dumps({
                        'type': 'pipeline_error',
                        'error': f'AI pipeline error: {str(e)}',
                        'session_id': session_id
                    }))
            else:
                logger.warning("[Turn Detection] ⚠️ Gemini API key not configured - AI pipeline disabled")
                ws.send(json.dumps({
                    'type': 'pipeline_error',
                    'error': 'Gemini API key not configured',
                    'session_id': session_id
                }))
            
            current_transcript = ""
            is_speaking = False
    
    def check_turn_timeout():
        """Check if turn should end due to timeout"""
        nonlocal last_speech_time, is_speaking
        if is_speaking and last_speech_time and (time.time() - last_speech_time) > turn_timeout:
            send_turn_end_notification()
    
    try:
        # Send connection established message
        ws.send(json.dumps({
            'type': 'status',
            'message': 'Turn detection connection established',
            'session_id': session_id,
            'turn_timeout': turn_timeout
        }))
        
        while True:
            data = ws.receive()
            if data is None:
                break
            
            # Try to parse as JSON first (for metadata)
            try:
                json_data = json.loads(data)
                if json_data.get('type') == 'start':
                    # Start new turn detection session
                    logger.info(f"[Turn Detection] Starting new session: {session_id}")
                    current_transcript = ""
                    last_speech_time = None
                    is_speaking = False
                    audio_chunks = []
                    transcription_buffer = []
                    last_transcription_time = time.time()
                    
                    ws.send(json.dumps({
                        'type': 'status',
                        'message': 'Turn detection started',
                        'session_id': session_id
                    }))
                    continue
                elif json_data.get('type') == 'stop':
                    # Stop turn detection and send final turn end
                    send_turn_end_notification()
                    ws.send(json.dumps({
                        'type': 'status',
                        'message': 'Turn detection stopped',
                        'session_id': session_id
                    }))
                    continue
                elif json_data.get('type') == 'ping':
                    # Keep-alive ping
                    ws.send(json.dumps({'type': 'pong'}))
                    continue
            except json.JSONDecodeError:
                # Not JSON, treat as binary audio data
                pass
            
            # Handle binary audio data for real-time transcription
            try:
                # Try to decode as base64 if it's a string
                if isinstance(data, str):
                    # Check if it looks like base64
                    if len(data) > 100 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in data):
                        audio_data = base64.b64decode(data)
                    else:
                        # Not base64, skip
                        continue
                else:
                    # Already binary data
                    audio_data = data
                
                # Store audio chunk
                audio_chunks.append(audio_data)
                transcription_buffer.append(audio_data)
                
                current_time = time.time()
                
                # Perform real-time transcription with turn detection every second
                if (transcription_buffer and 
                    current_time - last_transcription_time >= transcription_interval):
                    
                    try:
                        # Combine audio chunks for transcription
                        combined_audio = b''.join(transcription_buffer)
                        
                        # Create temporary file for transcription
                        temp_file = os.path.join(Config.UPLOAD_FOLDER, f"temp_turn_detection_{session_id}.webm")
                        with open(temp_file, 'wb') as f:
                            f.write(combined_audio)
                        
                        # Use AssemblyAI transcriber
                        transcriber = aai.Transcriber()
                        
                        # Transcribe the audio chunk
                        transcript = transcriber.transcribe(temp_file)
                        
                        # Clean up temporary file
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                        
                        if transcript.status == aai.TranscriptStatus.completed:
                            if transcript.text and transcript.text.strip():
                                # Update current transcript
                                current_transcript = transcript.text
                                last_speech_time = time.time()
                                is_speaking = True
                                
                                logger.info(f"[Turn Detection] 🎤 Speech detected: '{current_transcript}'")
                                
                                # Send real-time transcription update
                                ws.send(json.dumps({
                                    'type': 'transcription_update',
                                    'transcript': current_transcript,
                                    'timestamp': time.time(),
                                    'session_id': session_id,
                                    'is_speaking': True
                                }))
                            else:
                                # No speech detected, check for turn end
                                if is_speaking:
                                    check_turn_timeout()
                        else:
                            logger.warning(f"[Turn Detection] Transcription failed: {transcript.error}")
                            # Check for turn end even on transcription failure
                            if is_speaking:
                                check_turn_timeout()
                            
                    except Exception as e:
                        logger.error(f"[Turn Detection] Transcription error: {str(e)}")
                        # Check for turn end even on transcription error
                        if is_speaking:
                            check_turn_timeout()
                    
                    # Clear buffer after transcription
                    transcription_buffer = []
                    last_transcription_time = current_time
                
                # Send acknowledgment
                ws.send(json.dumps({
                    'type': 'chunk_received',
                    'chunk_size': len(audio_data),
                    'timestamp': time.time()
                }))
                
            except Exception as e:
                logger.error(f"[Turn Detection] Error processing audio chunk: {str(e)}")
                ws.send(json.dumps({
                    'type': 'error',
                    'message': f'Error processing audio: {str(e)}'
                }))
                
    except Exception as e:
        logger.error(f"[Turn Detection] Connection error: {str(e)}")
    finally:
        # Send final turn end notification if needed
        send_turn_end_notification()
        logger.info("[Turn Detection] Connection closed")


if __name__ == '__main__':
    logger.info("🎤 AI Voice Agent Server Starting...")
    logger.info("🌐 Server running at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
