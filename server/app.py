from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import requests
import json
from werkzeug.utils import secure_filename
import assemblyai as aai
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder='../client', static_folder='../client', static_url_path='')
CORS(app)

# In-memory chat history datastore
# Key: session_id, Value: list of messages [{role: 'user'/'assistant', content: 'text'}]
chat_history_store = {}

# Fallback responses for different error scenarios
FALLBACK_RESPONSES = {
    'stt_error': "I'm having trouble hearing you right now. Could you please try speaking again?",
    'llm_error': "I'm having trouble thinking right now. My AI brain seems to be taking a coffee break. Please try again in a moment.",
    'tts_error': "I'm having trouble speaking right now, but I'm still listening and thinking!",
    'general_error': "I'm experiencing some technical difficulties right now. Please bear with me while I get back on track.",
    'api_key_missing': "I'm not properly configured right now. Please check my settings and try again.",
    'timeout_error': "I'm taking a bit longer than usual to respond. Please try again in a moment."
}

def generate_fallback_audio(error_type='general_error'):
    """
    Generate a fallback response when TTS fails
    Returns a simple text response that the client can handle
    """
    return {
        'success': True,
        'audio_url': None,  # No audio available
        'fallback_text': FALLBACK_RESPONSES.get(error_type, FALLBACK_RESPONSES['general_error']),
        'error_type': error_type,
        'is_fallback': True
    }

def safe_murf_request(text, error_context='tts_error'):
    """
    Safely make a request to Murf API with comprehensive error handling
    """
    try:
        murf_api_key = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
        
        if murf_api_key == 'your_murf_api_key_here':
            print("⚠️ Murf API key not configured")
            return generate_fallback_audio('api_key_missing')
        
        murf_api_url = "https://api.murf.ai/v1/speech/generate"
        
        # Prepare the payload for Murf API
        murf_payload = {
            "voiceId": "en-US-ken",
            "style": "Conversational",
            "text": text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0
        }
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': murf_api_key
        }
        
        print(f"🎵 Attempting to generate audio for: {text[:50]}...")
        
        response = requests.post(
            murf_api_url,
            headers=headers,
            json=murf_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            murf_response = response.json()
            audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
            
            if audio_url:
                print(f"✅ Murf TTS successful")
                return {
                    'success': True,
                    'audio_url': audio_url,
                    'text': text,
                    'is_fallback': False
                }
            else:
                print("⚠️ Murf API returned no audio URL")
                return generate_fallback_audio(error_context)
        else:
            print(f"⚠️ Murf API error: {response.status_code}")
            return generate_fallback_audio(error_context)
            
    except requests.exceptions.Timeout:
        print("⚠️ Murf API timeout")
        return generate_fallback_audio('timeout_error')
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Murf API network error: {str(e)}")
        return generate_fallback_audio(error_context)
    except Exception as e:
        print(f"⚠️ Murf API unexpected error: {str(e)}")
        return generate_fallback_audio(error_context)

@app.route('/')
def index():
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
    aai_key = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
    gemini_key = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here') 
    murf_key = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
    
    return {
        'status': 'healthy', 
        'message': 'AI Voice Agent Backend is running!',
        'apis': {
            'assemblyai': 'configured' if aai_key != 'your_assemblyai_api_key_here' else 'not_configured',
            'gemini': 'configured' if gemini_key != 'your_gemini_api_key_here' else 'not_configured',
            'murf': 'configured' if murf_key != 'your_murf_api_key_here' else 'not_configured'
        },
        'error_handling': 'enabled'
    }

# Audio upload endpoint
@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part in the request'}), 400
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    file_info = {
        'name': filename,
        'content_type': file.content_type,
        'size': os.path.getsize(file_path)
    }
    return jsonify(file_info)

# Audio transcription endpoint
@app.route('/api/transcribe/file', methods=['POST'])
def transcribe_audio():

    aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
    
    if aai.settings.api_key == 'your_assemblyai_api_key_here':
        return jsonify({'error': 'AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY environment variable.'}), 500
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part in the request'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Read the audio file data directly from memory
        audio_data = file.read()
        
        transcriber = aai.Transcriber()
        
        transcript = transcriber.transcribe(audio_data)
        
        # Check if transcription was successful
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({'error': f'Transcription failed: {transcript.error}'}), 500
        
        # Return the transcription result
        return jsonify({
            'success': True,
            'transcript': transcript.text,
            'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None,
            'audio_duration': transcript.audio_duration if hasattr(transcript, 'audio_duration') else None
        })
        
    except Exception as e:
        return jsonify({'error': f'Transcription error: {str(e)}'}), 500

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
  
    try:
        # Get the request data
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text field in request'}), 400
        
        text = data['text']
        
        if not text.strip():
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        # Murf API configuration
        murf_api_url = "https://api.murf.ai/v1/speech/generate"
        
        # You'll need to set these environment variables or replace with actual values
        api_key = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
        
        if api_key == 'your_murf_api_key_here':
            return jsonify({'error': 'Murf API key not configured. Please set MURF_API_KEY environment variable.'}), 500
        
        # Prepare the payload for Murf API
        murf_payload = {
            "voiceId": "en-US-ken",  # Default voice, can be made configurable
            "style": "Conversational",
            "text": text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0
        }
        
        # Headers for Murf API
        headers = {
            'Content-Type': 'application/json',
            'api-key': api_key
        }
        
        # Make the request to Murf API
        response = requests.post(
            murf_api_url,
            headers=headers,
            json=murf_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            murf_response = response.json()
    
            audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
            
            if audio_url:
                return jsonify({
                    'success': True,
                    'audio_url': audio_url,
                    'text': text
                })
            else:
                return jsonify({'error': 'No audio URL received from Murf API'}), 500
        else:
            error_msg = f"Murf API error: {response.status_code}"
            try:
                error_detail = response.json().get('message', 'Unknown error')
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            
            return jsonify({'error': error_msg}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to Murf API timed out'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/tts/echo', methods=['POST'])
def tts_echo():
    """
    Echo Bot v2: Transcribe audio using AssemblyAI, then generate new audio with Murf voice
    """
    try:
        # Check if AssemblyAI API key is configured
        aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
        
        if aai.settings.api_key == 'your_assemblyai_api_key_here':
            return jsonify({'error': 'AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in .env file.'}), 500
        
        # Check if Murf API key is configured
        murf_api_key = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
        
        if murf_api_key == 'your_murf_api_key_here':
            return jsonify({'error': 'Murf API key not configured. Please set MURF_API_KEY in .env file.'}), 500
        
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file part in the request'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Step 1: Transcribe the audio using AssemblyAI
        print("🎤 Step 1: Transcribing audio with AssemblyAI...")
        audio_data = file.read()
        
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        
        # Check if transcription was successful
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({'error': f'Transcription failed: {transcript.error}'}), 500
        
        transcribed_text = transcript.text
        print(f"📝 Transcription result: {transcribed_text}")
        
        if not transcribed_text or not transcribed_text.strip():
            return jsonify({'error': 'No speech detected in the audio file'}), 400
        
        # Step 2: Generate new audio using Murf API
        print("🎵 Step 2: Generating new audio with Murf...")
        
        murf_api_url = "https://api.murf.ai/v1/speech/generate"
        
        # Prepare the payload for Murf API
        murf_payload = {
            "voiceId": "en-IN-isha",  # You can change this to any Murf voice
            "style": "Conversational",
            "text": transcribed_text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0
        }
        
        # Headers for Murf API
        headers = {
            'Content-Type': 'application/json',
            'api-key': murf_api_key
        }
        
        # Make the request to Murf API
        response = requests.post(
            murf_api_url,
            headers=headers,
            json=murf_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            murf_response = response.json()
            audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
            
            if audio_url:
                print(f"✅ Success! Audio generated: {audio_url}")
                return jsonify({
                    'success': True,
                    'transcription': transcribed_text,
                    'audio_url': audio_url,
                    'voice_id': "en-US-ken"
                })
            else:
                return jsonify({'error': 'No audio URL received from Murf API'}), 500
        else:
            error_msg = f"Murf API error: {response.status_code}"
            try:
                error_detail = response.json().get('message', 'Unknown error')
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            
            return jsonify({'error': error_msg}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out. Please try again.'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Echo processing error: {str(e)}'}), 500

@app.route('/api/llm/query', methods=['POST'])
def llm_query():
    """
    LLM Query endpoint: Accept audio input, transcribe it, send to Gemini API, and return Murf audio response
    """
    try:
        # Check if all API keys are configured
        aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
        gemini_api_key = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here')
        murf_api_key = os.getenv('MURF_API_KEY', 'your_murf_api_key_here')
        
        if aai.settings.api_key == 'your_assemblyai_api_key_here':
            return jsonify({'error': 'AssemblyAI API key not configured. Please set ASSEMBLYAI_API_KEY in .env file.'}), 500
        
        if gemini_api_key == 'your_gemini_api_key_here':
            return jsonify({'error': 'Gemini API key not configured. Please set GEMINI_API_KEY in .env file.'}), 500
        
        if murf_api_key == 'your_murf_api_key_here':
            return jsonify({'error': 'Murf API key not configured. Please set MURF_API_KEY in .env file.'}), 500
        
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file part in the request'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Step 1: Transcribe the audio using AssemblyAI
        print("🎤 Step 1: Transcribing audio with AssemblyAI...")
        audio_data = file.read()
        
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        
        # Check if transcription was successful
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({'error': f'Transcription failed: {transcript.error}'}), 500
        
        transcribed_text = transcript.text
        print(f"📝 Transcription result: {transcribed_text}")
        
        if not transcribed_text or not transcribed_text.strip():
            return jsonify({'error': 'No speech detected in the audio file'}), 400
        
        # Step 2: Send transcribed text to Gemini LLM
        print("🤖 Step 2: Generating LLM response with Gemini...")
        genai.configure(api_key=gemini_api_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        llm_response = model.generate_content(transcribed_text)
        
        if not llm_response.text:
            return jsonify({'error': 'No response generated from Gemini API'}), 500
        
        llm_text = llm_response.text
        print(f"💭 LLM Response: {llm_text[:100]}...")
        
        # Step 3: Generate audio from LLM response using Murf
        print("🎵 Step 3: Generating audio response with Murf...")
        
        murf_api_url = "https://api.murf.ai/v1/speech/generate"
        
        # Prepare the payload for Murf API
        murf_payload = {
            "voiceId": "en-US-ken",  # You can change this to any Murf voice
            "style": "Conversational",
            "text": llm_text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False,
            "variation": 1,
            "audioDuration": 0
        }
        
        # Headers for Murf API
        headers = {
            'Content-Type': 'application/json',
            'api-key': murf_api_key
        }
        
        # Make the request to Murf API
        response = requests.post(
            murf_api_url,
            headers=headers,
            json=murf_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            murf_response = response.json()
            audio_url = murf_response.get('audioFile', murf_response.get('url', ''))
            
            if audio_url:
                print(f"✅ Success! LLM audio response generated: {audio_url}")
                return jsonify({
                    'success': True,
                    'transcription': transcribed_text,
                    'llm_response': llm_text,
                    'audio_url': audio_url,
                    'voice_id': "en-US-ken",
                    'model': 'gemini-1.5-flash'
                })
            else:
                return jsonify({'error': 'No audio URL received from Murf API'}), 500
        else:
            error_msg = f"Murf API error: {response.status_code}"
            try:
                error_detail = response.json().get('message', 'Unknown error')
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            
            return jsonify({'error': error_msg}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out. Please try again.'}), 408
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        print(f"❌ LLM Query error: {str(e)}")
        return jsonify({'error': f'LLM query error: {str(e)}'}), 500

@app.route('/api/agent/chat/<session_id>', methods=['POST'])
def agent_chat(session_id):
    """
    Agent Chat endpoint: Accept audio input, maintain chat history, and return Murf audio response with robust error handling
    """
    try:
        print(f"💬 Starting chat session: {session_id}")
        
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({
                'error': 'No audio file provided',
                'fallback_audio': generate_fallback_audio('general_error')
            }), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({
                'error': 'No audio file selected',
                'fallback_audio': generate_fallback_audio('general_error')
            }), 400
        
        # Step 1: Transcribe the audio using AssemblyAI with error handling
        print("🎤 Step 1: Transcribing audio with AssemblyAI...")
        transcribed_text = None
        
        try:
            aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
            
            if aai.settings.api_key == 'your_assemblyai_api_key_here':
                print("⚠️ AssemblyAI API key not configured")
                fallback = generate_fallback_audio('api_key_missing')
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'user_message': '[Speech Recognition Unavailable]',
                    'assistant_response': fallback['fallback_text'],
                    'audio_url': fallback['audio_url'],
                    'message_count': 1,
                    'is_fallback': True,
                    'error_type': 'stt_error'
                })
            
            audio_data = file.read()
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_data)
            
            if transcript.status == aai.TranscriptStatus.error:
                print(f"⚠️ AssemblyAI transcription error: {transcript.error}")
                raise Exception(f"Transcription failed: {transcript.error}")
            
            transcribed_text = transcript.text
            print(f"📝 Transcription result: {transcribed_text}")
            
            if not transcribed_text or not transcribed_text.strip():
                print("⚠️ No speech detected in audio")
                transcribed_text = "[No speech detected]"
            
        except Exception as e:
            print(f"⚠️ STT Error: {str(e)}")
            transcribed_text = "[Speech recognition failed]"
            fallback = generate_fallback_audio('stt_error')
            return jsonify({
                'success': True,
                'session_id': session_id,
                'user_message': transcribed_text,
                'assistant_response': fallback['fallback_text'],
                'audio_url': fallback['audio_url'],
                'message_count': 1,
                'is_fallback': True,
                'error_type': 'stt_error'
            })
        
        # Step 2: Manage chat history
        print("📚 Step 2: Managing chat history...")
        if session_id not in chat_history_store:
            chat_history_store[session_id] = []
        
        chat_history_store[session_id].append({
            'role': 'user',
            'content': transcribed_text
        })
        
        conversation_history = chat_history_store[session_id]
        print(f"💾 Chat history length: {len(conversation_history)} messages")
        
        # Step 3: Generate LLM response with error handling
        print("🤖 Step 3: Generating LLM response...")
        llm_text = None
        
        try:
            gemini_api_key = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here')
            
            if gemini_api_key == 'your_gemini_api_key_here':
                print("⚠️ Gemini API key not configured")
                raise Exception("Gemini API key not configured")
            
            genai.configure(api_key=gemini_api_key)
            
            # Build context for Gemini
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            context_messages = []
            
            for msg in recent_history[:-1]:  # Exclude current message
                if msg['role'] == 'user':
                    context_messages.append(f"User: {msg['content']}")
                else:
                    context_messages.append(f"Assistant: {msg['content']}")
            
            if context_messages:
                full_prompt = "Previous conversation:\n" + "\n".join(context_messages) + f"\n\nUser: {transcribed_text}\n\nAssistant:"
            else:
                full_prompt = transcribed_text
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            llm_response = model.generate_content(full_prompt)
            
            if not llm_response.text:
                raise Exception("No response generated from Gemini")
            
            llm_text = llm_response.text
            print(f"💭 LLM Response: {llm_text[:100]}...")
            
        except Exception as e:
            print(f"⚠️ LLM Error: {str(e)}")
            llm_text = FALLBACK_RESPONSES['llm_error']
        
        # Add assistant response to chat history
        chat_history_store[session_id].append({
            'role': 'assistant',
            'content': llm_text
        })
        
        # Step 4: Generate audio with robust error handling
        print("🎵 Step 4: Generating audio response...")
        audio_result = safe_murf_request(llm_text, 'tts_error')
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user_message': transcribed_text,
            'assistant_response': llm_text,
            'audio_url': audio_result.get('audio_url'),
            'fallback_text': audio_result.get('fallback_text'),
            'message_count': len(chat_history_store[session_id]),
            'voice_id': "en-US-ken",
            'model': 'gemini-1.5-flash',
            'is_fallback': audio_result.get('is_fallback', False),
            'error_type': audio_result.get('error_type')
        })
            
    except Exception as e:
        print(f"❌ Agent Chat critical error: {str(e)}")
        fallback = generate_fallback_audio('general_error')
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user_message': '[Error processing request]',
            'assistant_response': fallback['fallback_text'],
            'audio_url': fallback['audio_url'],
            'message_count': 1,
            'is_fallback': True,
            'error_type': 'general_error'
        })

# Helper endpoint to get chat history for a session
@app.route('/api/agent/chat/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a specific session"""
    if session_id in chat_history_store:
        return jsonify({
            'session_id': session_id,
            'messages': chat_history_store[session_id],
            'message_count': len(chat_history_store[session_id])
        })
    else:
        return jsonify({
            'session_id': session_id,
            'messages': [],
            'message_count': 0
        })

# Helper endpoint to clear chat history for a session
@app.route('/api/agent/chat/<session_id>/clear', methods=['DELETE'])
def clear_chat_history(session_id):
    """Clear chat history for a specific session"""
    if session_id in chat_history_store:
        del chat_history_store[session_id]
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Chat history cleared'
    })

if __name__ == '__main__':
    print("🎤 AI Voice Agent Server Starting...")
    print("🌐 Server running at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
