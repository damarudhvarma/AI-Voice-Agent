from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
import os

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

# Setup logging
logger = setup_logger()

# Create Flask app
app = Flask(__name__, template_folder='../client', static_folder='../client', static_url_path='')
CORS(app)

# Configure app
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file upload size limit exceeded"""
    logger.warning("File upload size limit exceeded")
    return jsonify(ErrorResponse(
        error="File too large. Maximum size is 16MB."
    ).dict()), 413


@app.errorhandler(Exception)
def handle_generic_error(e):
    """Handle generic errors"""
    logger.error(f"Unhandled error: {str(e)}")
    return jsonify(ErrorResponse(
        error="Internal server error. Please try again."
    ).dict()), 500


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


if __name__ == '__main__':
    logger.info("🎤 AI Voice Agent Server Starting...")
    logger.info("🌐 Server running at: http://localhost:5000")
    logger.info(f"📁 Upload directory: {Config.UPLOAD_FOLDER}")
    logger.info(f"🔧 API Status: {Config.get_api_status()}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
