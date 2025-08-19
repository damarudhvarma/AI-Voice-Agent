from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_sock import Sock
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
sock = Sock(app)

# Raw WebSocket endpoint for audio streaming
@sock.route('/ws/audio')
def websocket_audio(ws):
    """
    WebSocket endpoint for receiving audio data from client
    Saves received audio chunks to files and transcribes in real-time
    """
    import time
    import base64
    import io
    import wave
    import struct
    import tempfile
    import os
    
    # Import pydub for audio conversion
    try:
        from pydub import AudioSegment
        from pydub.utils import make_chunks
        pydub_available = True
        
        # Try to set FFmpeg path to local installation
        import os
        # Check multiple possible FFmpeg locations
        possible_ffmpeg_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ffmpeg.exe'),  # Project root
            os.path.join(os.getcwd(), 'ffmpeg.exe'),  # Current working directory
            'ffmpeg.exe',  # In PATH
            'C:\\ffmpeg\\bin\\ffmpeg.exe',  # Common Windows installation
        ]
        
        ffmpeg_found = False
        for ffmpeg_path in possible_ffmpeg_paths:
            if os.path.exists(ffmpeg_path):
                try:
                    # Set FFmpeg path for pydub
                    import pydub
                    pydub.AudioSegment.converter = ffmpeg_path
                    pydub.AudioSegment.ffmpeg = ffmpeg_path
                    print(f"[WebSocket] Using FFmpeg: {ffmpeg_path}")
                    ffmpeg_found = True
                    break
                except Exception as e:
                    print(f"[WebSocket] Failed to set FFmpeg path {ffmpeg_path}: {e}")
                    continue
        
        if not ffmpeg_found:
            print(f"[WebSocket] FFmpeg not found in any of the expected locations")
            print(f"[WebSocket] Searched paths: {possible_ffmpeg_paths}")
        
        print(f"[WebSocket] Pydub audio processing available")
    except ImportError:
        pydub_available = False
        print(f"[WebSocket] Pydub not available - using basic audio processing")
    
    print(f"[WebSocket] Audio streaming connection established")
    
    # Initialize AssemblyAI transcriber
    aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY', 'your_assemblyai_api_key_here')
    transcriber = None
    
    if aai.settings.api_key != 'your_assemblyai_api_key_here':
        try:
            transcriber = aai.Transcriber()
            print(f"[WebSocket] AssemblyAI transcriber initialized successfully")
        except Exception as e:
            print(f"[WebSocket] Failed to initialize AssemblyAI transcriber: {str(e)}")
            transcriber = None
    else:
        print(f"[WebSocket] AssemblyAI API key not configured - transcription disabled")
    
    # Create uploads directory if it doesn't exist
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Generate unique session ID for this connection
    session_id = f"ws_session_{int(time.time())}_{int(time.time() * 1000) % 1000}"
    current_file_path = None
    audio_chunks = []
    transcription_buffer = []
    last_transcription_time = 0
    transcription_interval = 3.0  # Transcribe every 3 seconds
    audio_format = None  # Will be detected from first chunk
    
    def create_wav_file(audio_data, sample_rate=16000, channels=1):
        """Convert raw audio data to WAV format (improved method)"""
        try:
            print(f"[WebSocket] Creating improved WAV file from {len(audio_data)} bytes of audio data")
            
            # Check if the data looks like it might be valid audio
            if len(audio_data) < 100:
                print(f"[WebSocket] Audio data too small, might not be valid")
                return None
            
            # For WebM/Opus data, we need to create a proper WAV file
            # Since we can't decode the WebM/Opus without FFmpeg, we'll create a WAV file
            # that AssemblyAI might be able to process, or we'll send the original data
            
            # First, try to create a simple WAV file with the raw data
            try:
                # Create WAV file in memory with proper headers
                wav_buffer = io.BytesIO()
                
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(2)  # 16-bit audio
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data)
                
                wav_data = wav_buffer.getvalue()
                print(f"[WebSocket] Basic WAV file created: {len(wav_data)} bytes")
                
                # Check if the WAV file looks valid
                if len(wav_data) > 44:  # WAV header is 44 bytes
                    return wav_data
                else:
                    print(f"[WebSocket] WAV file too small, might be invalid")
                    return None
                
            except Exception as e:
                print(f"[WebSocket] Could not create WAV file: {str(e)}")
                return None
                
        except Exception as e:
            print(f"[WebSocket] Error creating WAV file: {str(e)}")
            return None
    
    def convert_audio_to_wav(audio_data, format_type='webm'):
        """Convert audio data to WAV format using improved methods"""
        try:
            print(f"[WebSocket] Converting audio from {format_type} to WAV (data size: {len(audio_data)} bytes)")
            
            # Try pydub first if available and FFmpeg is working
            if pydub_available:
                try:
                    # Create temporary file with the original format
                    with tempfile.NamedTemporaryFile(suffix=f'.{format_type}', delete=False) as temp_in:
                        temp_in.write(audio_data)
                        temp_in_path = temp_in.name
                    
                    print(f"[WebSocket] Created temporary input file: {temp_in_path}")
                    
                    # Convert to WAV using pydub
                    try:
                        audio = AudioSegment.from_file(temp_in_path, format=format_type)
                        print(f"[WebSocket] Audio loaded: {len(audio)}ms, {audio.channels} channels, {audio.frame_rate}Hz")
                    except Exception as e:
                        print(f"[WebSocket] Error loading audio with pydub: {str(e)}")
                        # Try with auto-detection
                        try:
                            audio = AudioSegment.from_file(temp_in_path)
                            print(f"[WebSocket] Audio loaded with auto-detection: {len(audio)}ms")
                        except Exception as e2:
                            print(f"[WebSocket] Auto-detection also failed: {str(e2)}")
                            raise e2
                    
                    # Export as WAV with proper settings for AssemblyAI
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_out:
                        try:
                            # Use settings that AssemblyAI prefers
                            audio.export(temp_out.name, format='wav', 
                                       parameters=['-ar', '16000', '-ac', '1', '-sample_fmt', 's16'])
                            temp_out_path = temp_out.name
                            print(f"[WebSocket] Audio exported to WAV: {temp_out_path}")
                        except Exception as e:
                            print(f"[WebSocket] Error exporting to WAV: {str(e)}")
                            # Try without parameters
                            audio.export(temp_out.name, format='wav')
                            temp_out_path = temp_out.name
                            print(f"[WebSocket] Audio exported to WAV (without parameters): {temp_out_path}")
                    
                    # Read the converted WAV file
                    with open(temp_out_path, 'rb') as f:
                        wav_data = f.read()
                    
                    print(f"[WebSocket] WAV conversion successful: {len(wav_data)} bytes")
                    
                    # Clean up temporary files
                    try:
                        os.unlink(temp_in_path)
                        os.unlink(temp_out_path)
                        print(f"[WebSocket] Temporary files cleaned up")
                    except Exception as e:
                        print(f"[WebSocket] Warning: Could not clean up temporary files: {str(e)}")
                    
                    return wav_data
                    
                except Exception as e:
                    print(f"[WebSocket] Pydub conversion failed: {str(e)}")
                    print(f"[WebSocket] Falling back to basic conversion")
            
            # Fallback: Try to send original WebM data to AssemblyAI
            if format_type == 'webm':
                print(f"[WebSocket] Sending original WebM data to AssemblyAI (size: {len(audio_data)} bytes)")
                return audio_data  # AssemblyAI can handle WebM directly
            else:
                # For other formats, try the basic WAV creation
                return create_wav_file(audio_data)
            
        except Exception as e:
            print(f"[WebSocket] Error converting audio to WAV: {str(e)}")
            print(f"[WebSocket] Returning original audio data")
            return audio_data
    
    def detect_audio_format(audio_data, format_hint=None):
        """Detect audio format from the first chunk or format hint"""
        if format_hint:
            # Handle MIME type strings (e.g., 'audio/webm;codecs=opus')
            format_hint_lower = format_hint.lower()
            
            # Extract format from MIME type
            if 'audio/' in format_hint_lower:
                # Extract the part after 'audio/'
                format_part = format_hint_lower.split('audio/')[1]
                # Remove codec info if present
                if ';' in format_part:
                    format_part = format_part.split(';')[0]
                
                if format_part in ['webm', 'mp4', 'wav', 'mp3', 'ogg']:
                    return format_part
                elif format_part == 'mpeg':
                    return 'mp3'
                else:
                    # Default to webm for unknown audio formats
                    return 'webm'
            
            # Handle simple format hints
            if 'webm' in format_hint_lower:
                return 'webm'
            elif 'mp4' in format_hint_lower:
                return 'mp4'
            elif 'wav' in format_hint_lower:
                return 'wav'
            elif 'mp3' in format_hint_lower:
                return 'mp3'
        
        if len(audio_data) < 4:
            return 'webm'  # Default to webm for MediaRecorder
        
        # Check for common audio format headers
        if audio_data[:4] == b'RIFF':  # WAV
            return 'wav'
        elif audio_data[:4] == b'fLaC':  # FLAC
            return 'flac'
        elif audio_data[:4] == b'ID3' or audio_data[:3] == b'\xff\xfb\x90':  # MP3
            return 'mp3'
        elif audio_data[:4] == b'\x1a\x45\xdf\xa3':  # WebM/MKV
            return 'webm'
        elif audio_data[:4] == b'ftyp':  # MP4
            return 'mp4'
        else:
            # Assume WebM for MediaRecorder
            return 'webm'
    
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
                    current_file_path = os.path.join(upload_folder, filename)
                    audio_chunks = []
                    transcription_buffer = []
                    last_transcription_time = time.time()
                    
                    # Extract format from MIME type (e.g., 'audio/webm;codecs=opus' -> 'webm')
                    raw_audio_format = json_data.get('audioFormat', 'webm')
                    audio_format = detect_audio_format(b'', raw_audio_format)
                    
                    print(f"[WebSocket] Starting new recording: {filename} (format: {audio_format} from '{raw_audio_format}')")
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
                            
                            # Convert to WAV format
                            wav_data = convert_audio_to_wav(combined_audio, audio_format)
                            if wav_data:
                                with open(current_file_path, 'wb') as f:
                                    f.write(wav_data)
                                file_size = os.path.getsize(current_file_path)
                                print(f"[WebSocket] Recording saved: {current_file_path} ({file_size} bytes)")
                                
                                # Final transcription of complete audio
                                if transcriber:
                                    try:
                                        print(f"[WebSocket] Performing final transcription...")
                                        transcript = transcriber.transcribe(current_file_path)
                                        
                                        if transcript.status == aai.TranscriptStatus.completed:
                                            print(f"🎤 FINAL TRANSCRIPTION: {transcript.text}")
                                            ws.send(json.dumps({
                                                'type': 'final_transcription',
                                                'transcript': transcript.text,
                                                'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None
                                            }))
                                        else:
                                            print(f"[WebSocket] Final transcription failed: {transcript.error}")
                                    except Exception as e:
                                        print(f"[WebSocket] Final transcription error: {str(e)}")
                            else:
                                print(f"[WebSocket] Failed to create WAV file")
                                
                        except Exception as e:
                            print(f"[WebSocket] Error saving audio file: {str(e)}")
                        
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
                print(f"[WebSocket] Received audio chunk: {len(audio_data)} bytes (total: {sum(len(chunk) for chunk in audio_chunks)} bytes)")
                
                # Perform real-time transcription every few seconds
                if (transcriber and 
                    transcription_buffer and 
                    current_time - last_transcription_time >= transcription_interval):
                    
                    try:
                        print(f"[WebSocket] Performing real-time transcription...")
                        
                        # Create temporary WAV file for transcription
                        combined_audio = b''.join(transcription_buffer)
                        wav_data = convert_audio_to_wav(combined_audio, audio_format)
                        
                        if wav_data:
                            transcript = None
                            
                            # Try different approaches for transcription
                            transcription_attempts = []
                            
                            # Attempt 1: Try with converted WAV file
                            if audio_format != 'webm' or len(wav_data) > 1000:  # Only try WAV if it's not WebM or if it's substantial
                                try:
                                    temp_file = os.path.join(upload_folder, f"temp_transcription_{session_id}.wav")
                                    with open(temp_file, 'wb') as f:
                                        f.write(wav_data)
                                    
                                    transcript = transcriber.transcribe(temp_file)
                                    transcription_attempts.append(f"WAV file ({len(wav_data)} bytes)")
                                    
                                    # Clean up temporary file
                                    try:
                                        os.remove(temp_file)
                                    except:
                                        pass
                                        
                                except Exception as e:
                                    print(f"[WebSocket] Error transcribing WAV file: {str(e)}")
                            
                            # Attempt 2: Try with original audio data
                            if not transcript or transcript.status == aai.TranscriptStatus.error:
                                try:
                                    print(f"[WebSocket] Trying transcription with original audio data...")
                                    transcript = transcriber.transcribe(combined_audio)
                                    transcription_attempts.append(f"Original data ({len(combined_audio)} bytes)")
                                except Exception as e:
                                    print(f"[WebSocket] Transcription with original data also failed: {str(e)}")
                            
                            # Attempt 3: Try with WebM file (if original format is WebM)
                            if (not transcript or transcript.status == aai.TranscriptStatus.error) and audio_format == 'webm':
                                try:
                                    print(f"[WebSocket] Trying transcription with WebM file...")
                                    webm_file = os.path.join(upload_folder, f"temp_transcription_{session_id}.webm")
                                    with open(webm_file, 'wb') as f:
                                        f.write(combined_audio)
                                    transcript = transcriber.transcribe(webm_file)
                                    transcription_attempts.append(f"WebM file ({len(combined_audio)} bytes)")
                                    
                                    # Clean up WebM file
                                    try:
                                        os.remove(webm_file)
                                    except:
                                        pass
                                        
                                except Exception as e:
                                    print(f"[WebSocket] Transcription with WebM file also failed: {str(e)}")
                            
                            # Log transcription attempts
                            if transcription_attempts:
                                print(f"[WebSocket] Transcription attempts: {', '.join(transcription_attempts)}")
                            
                            if transcript and transcript.status == aai.TranscriptStatus.completed:
                                print(f"🎤 REAL-TIME TRANSCRIPTION: {transcript.text}")
                                ws.send(json.dumps({
                                    'type': 'transcription',
                                    'transcript': transcript.text,
                                    'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None,
                                    'timestamp': current_time
                                }))
                            elif transcript:
                                print(f"[WebSocket] Real-time transcription failed: {transcript.error}")
                                # Send empty transcription to indicate failure
                                ws.send(json.dumps({
                                    'type': 'transcription',
                                    'transcript': '',
                                    'confidence': 0,
                                    'timestamp': current_time,
                                    'error': transcript.error
                                }))
                            else:
                                print(f"[WebSocket] All transcription attempts failed")
                                # Send empty transcription to indicate failure
                                ws.send(json.dumps({
                                    'type': 'transcription',
                                    'transcript': '',
                                    'confidence': 0,
                                    'timestamp': current_time,
                                    'error': 'All transcription methods failed'
                                }))
                        else:
                            print(f"[WebSocket] Failed to create audio data for transcription")
                            # Send empty transcription to indicate failure
                            ws.send(json.dumps({
                                'type': 'transcription',
                                'transcript': '',
                                'confidence': 0,
                                'timestamp': current_time,
                                'error': 'Failed to create audio data'
                            }))
                        
                        # Clear buffer after transcription
                        transcription_buffer = []
                        last_transcription_time = current_time
                        
                    except Exception as e:
                        print(f"[WebSocket] Real-time transcription error: {str(e)}")
                        # Don't clear buffer on error, let it accumulate
                
                # Send acknowledgment
                ws.send(json.dumps({
                    'type': 'chunk_received',
                    'chunk_size': len(audio_data),
                    'total_size': sum(len(chunk) for chunk in audio_chunks)
                }))
                
            except Exception as e:
                print(f"[WebSocket] Error processing audio chunk: {str(e)}")
                ws.send(json.dumps({
                    'type': 'error',
                    'message': f'Error processing audio: {str(e)}'
                }))
                
    except Exception as e:
        print(f"[WebSocket] Connection error: {str(e)}")
    finally:
        # Save any remaining audio data
        if current_file_path and audio_chunks:
            try:
                combined_audio = b''.join(audio_chunks)
                wav_data = convert_audio_to_wav(combined_audio, audio_format)
                if wav_data:
                    with open(current_file_path, 'wb') as f:
                        f.write(wav_data)
                    file_size = os.path.getsize(current_file_path)
                    print(f"[WebSocket] Final recording saved: {current_file_path} ({file_size} bytes)")
                    
                    # Final transcription if we have a transcriber
                    if transcriber:
                        try:
                            print(f"[WebSocket] Performing final transcription on saved audio...")
                            transcript = transcriber.transcribe(current_file_path)
                            
                            if transcript.status == aai.TranscriptStatus.completed:
                                print(f"🎤 FINAL TRANSCRIPTION: {transcript.text}")
                            else:
                                print(f"[WebSocket] Final transcription failed: {transcript.error}")
                        except Exception as e:
                            print(f"[WebSocket] Final transcription error: {str(e)}")
            except Exception as e:
                print(f"[WebSocket] Error in final save: {str(e)}")
        
        print(f"[WebSocket] Audio streaming connection closed")

# Raw WebSocket endpoint for echo testing (works with Postman)
@sock.route('/ws')
def websocket_echo(ws):
    while True:
        data = ws.receive()
        if data is None:
            break
        print(f"[WebSocket] Received: {data}")
        ws.send(data)

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

@app.route('/websocket_test.html')
def websocket_test():
    """Serve the WebSocket test page"""
    return send_from_directory('../client', 'websocket_test.html')

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
