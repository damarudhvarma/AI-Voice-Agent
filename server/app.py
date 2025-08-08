from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import requests
import json
from werkzeug.utils import secure_filename
import assemblyai as aai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder='../client', static_folder='../client', static_url_path='')
CORS(app)

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
    return {'status': 'healthy', 'message': 'AI Voice Agent Backend is running!'}

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

if __name__ == '__main__':
    print("🎤 AI Voice Agent Server Starting...")
    print("🌐 Server running at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
